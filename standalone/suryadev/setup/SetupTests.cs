using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using SuryadevSetup;

static class BootstrapTests {
    static int passed;
    static Action<string,int> progress=(s,p)=>{};
    static void Check(bool condition,string message) {if(!condition)throw new Exception(message);}
    static void Test(string name,Action action) {action();Console.WriteLine("PASS "+name);passed++;}
    static void Refuses(Action action) {try{action();}catch(Exception){return;}throw new Exception("Unsafe operation was accepted");}
    static string NewRoot(string basePath) {return Path.Combine(basePath,Guid.NewGuid().ToString("N").Substring(0,8));}
    static string Zip(string dir,string fake,params string[] names) {
        string path=Path.Combine(dir,Guid.NewGuid().ToString("N")+".zip");
        using(var file=File.Create(path)) using(var zip=new ZipArchive(file,ZipArchiveMode.Create)) {
            foreach(string name in names) {
                var entry=zip.CreateEntry(name);
                using(var output=entry.Open()) {
                    byte[] bytes=name.EndsWith(".exe")?File.ReadAllBytes(fake):Encoding.UTF8.GetBytes("source fixture");
                    output.Write(bytes,0,bytes.Length);
                }
            }
        }
        return path;
    }
    sealed class Server : IDisposable {
        TcpListener listener; Thread thread; volatile bool running=true;
        public string Origin; public int Requests;
        byte[] bytes;
        public Server(byte[] data) {
            bytes=data;listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
            Origin="http://127.0.0.1:"+((IPEndPoint)listener.LocalEndpoint).Port;
            thread=new Thread(Serve);thread.IsBackground=true;thread.Start();
        }
        void Serve() {
            while(running) try {
                using(var client=listener.AcceptTcpClient()) using(var stream=client.GetStream()) {
                    var reader=new StreamReader(stream,Encoding.ASCII,false,1024,true);
                    string first=reader.ReadLine();string route=first.Split(' ')[1];
                    string line;while(!String.IsNullOrEmpty(line=reader.ReadLine())){}
                    Requests++;
                    if(route=="/redirect") {Write(stream,"HTTP/1.1 302 Found\r\nLocation: /ok\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");continue;}
                    if(route=="/unsafe-redirect") {Write(stream,"HTTP/1.1 302 Found\r\nLocation: http://8.8.8.8/payload\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");continue;}
                    if(route=="/missing") {Write(stream,"HTTP/1.1 404 Missing\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");continue;}
                    Write(stream,"HTTP/1.1 200 OK\r\nContent-Length: "+bytes.Length+"\r\nConnection: close\r\n\r\n");
                    byte[] actual=(byte[])bytes.Clone();if(route=="/bad") actual[0]^=1;
                    stream.Write(actual,0,route=="/short"?actual.Length/2:actual.Length);
                }
            } catch {if(!running)return;}
        }
        static void Write(Stream stream,string text) {byte[] b=Encoding.ASCII.GetBytes(text);stream.Write(b,0,b.Length);}
        public void Dispose() {running=false;listener.Stop();thread.Join(2000);}
    }
    static int Main(string[] args) {
        try {
            string basePath=Path.GetFullPath(args[0]);Directory.CreateDirectory(basePath);
            string fake=Path.GetFullPath(args[1]), log=Path.Combine(basePath,"executed.log");
            Environment.SetEnvironmentVariable("SURYADEV_TEST_EXECUTIONS",log);
            Test("HTTPS required for public downloads",()=>Refuses(()=>Engine.ValidateUrl("http://8.8.8.8/file.zip")));
            Test("private LAN is accepted with a pinned checksum",()=>Check(Engine.ValidateUrl("http://192.168.1.20/app.zip").Scheme=="http","LAN rejected"));
            Test("credential-bearing URL rejected",()=>Refuses(()=>Engine.ValidateUrl("https://user:secret@example.com/app.zip")));
            Test("query token URL rejected",()=>Refuses(()=>Engine.ValidateUrl("https://example.com/app.zip?token=secret")));
            Test("network share install rejected",()=>Refuses(()=>Engine.ValidateRoot(@"\\server\share\app")));
            Test("drive root rejected",()=>Refuses(()=>Engine.ValidateRoot(Path.GetPathRoot(basePath))));
            Test("unmarked existing files preserved",()=>{
                string root=NewRoot(basePath);Directory.CreateDirectory(root);File.WriteAllText(Path.Combine(root,"user.txt"),"keep");
                Refuses(()=>Engine.ValidateRoot(root));Check(File.ReadAllText(Path.Combine(root,"user.txt"))=="keep","User file changed");
            });
            string valid=Zip(basePath,fake,"Suryadev-Learner/Suryadev-Learner.exe","Suryadev-Learner/_internal/app/dashboard.html");
            byte[] body=File.ReadAllBytes(valid);
            using(var server=new Server(body)) {
                var spec=new Payload(server.Origin+"/ok",Engine.HashFile(valid),Engine.HashFile(fake),body.Length,"test");
                Test("good LAN download verifies checksum",()=>{
                    string target=Path.Combine(basePath,"download.zip");Engine.Download(new Uri(spec.Url),target,spec,progress,CancellationToken.None);
                    Check(Engine.HashFile(target)==spec.Hash,"Downloaded bytes differ");
                });
                Test("same-LAN redirect works",()=>Engine.Download(new Uri(server.Origin+"/redirect"),Path.Combine(basePath,"redirect.zip"),spec,progress,CancellationToken.None));
                Test("HTTP redirect cannot leave the approved LAN server",()=>Refuses(()=>Engine.Download(new Uri(server.Origin+"/unsafe-redirect"),Path.Combine(basePath,"redirect-bad.zip"),spec,progress,CancellationToken.None)));
                Test("corrupted download rejected before execution",()=>{
                    int before=File.Exists(log)?File.ReadAllLines(log).Length:0;
                    Refuses(()=>Engine.Download(new Uri(server.Origin+"/bad"),Path.Combine(basePath,"bad.zip"),spec,progress,CancellationToken.None));
                    Check((File.Exists(log)?File.ReadAllLines(log).Length:0)==before,"Downloaded code executed");
                });
                Test("interrupted download rejected",()=>Refuses(()=>Engine.Download(new Uri(server.Origin+"/short"),Path.Combine(basePath,"short.zip"),spec,progress,CancellationToken.None)));
                Test("404 is an explicit failure",()=>Refuses(()=>Engine.Download(new Uri(server.Origin+"/missing"),Path.Combine(basePath,"missing.zip"),spec,progress,CancellationToken.None)));
                Test("cancelled transfer rejected",()=>{var cancel=new CancellationTokenSource();cancel.Cancel();Refuses(()=>Engine.Download(new Uri(spec.Url),Path.Combine(basePath,"cancel.zip"),spec,progress,cancel.Token));});
                Test("complete install runs verifier and components",()=>{
                    string root=Path.Combine(basePath,"path with spaces");var receipt=Engine.Install(root,spec.Url,spec,false,progress,CancellationToken.None);
                    Check(receipt.ComponentState=="ready" && !receipt.ComponentsSkipped,"False setup outcome");
                    Check(receipt.Data==Path.Combine(root,"data"),"Unstable data path");
                    Check(File.ReadAllLines(log).Any(x=>x.Contains(receipt.Data)),"Data path argument split at spaces");
                    File.WriteAllText(Path.Combine(receipt.Data,"old-learning.txt"),"immutable learning");
                    int requests=server.Requests;
                    var second=Engine.Install(root,spec.Url,spec,false,progress,CancellationToken.None);
                    Check(File.ReadAllText(Path.Combine(second.Data,"old-learning.txt"))=="immutable learning","Learning changed");
                    Check(server.Requests==requests,"Verified cache was redownloaded");
                });
                Test("failed new download preserves previous active version",()=>{
                    string root=NewRoot(basePath);Directory.CreateDirectory(root);
                    Engine.Save(root,new Receipt{Version="old",Exe="existing.exe",Data=Path.Combine(root,"data")});
                    var broken=new Payload(server.Origin+"/bad",spec.Hash,spec.ExeHash,spec.Bytes,"new");
                    Refuses(()=>Engine.Install(root,broken.Url,broken,false,progress,CancellationToken.None));
                    Check(Engine.Json.Deserialize<Receipt>(File.ReadAllText(Path.Combine(root,Engine.Marker))).Version=="old","Rollback lost prior active version");
                });
                Test("installer cross-process lock excludes duplicate install",()=>{
                    string root=NewRoot(basePath);Directory.CreateDirectory(root);Engine.Save(root,new Receipt());
                    using(var held=new FileStream(Path.Combine(root,".setup.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))
                        Refuses(()=>Engine.Install(root,spec.Url,spec,true,progress,CancellationToken.None));
                });
            }
            foreach(string unsafePath in new[]{"Suryadev-Learner/../../escape.txt","C:/escape.txt","Suryadev-Learner/C:/escape.txt","Suryadev-Learner/./alias.txt"}) {
                string item=unsafePath;
                Test("archive path refused: "+item,()=>{
                    string zip=Zip(basePath,fake,item);string root=NewRoot(basePath);Directory.CreateDirectory(root);
                    Refuses(()=>Engine.Extract(zip,root,progress,CancellationToken.None));
                    Check(!Directory.EnumerateFileSystemEntries(root).Any(),"Archive wrote before path validation");
                });
            }
            Test("duplicate archive names refused before extraction",()=>{
                string zip=Zip(basePath,fake,"Suryadev-Learner/a.txt","Suryadev-Learner/A.txt");
                string root=NewRoot(basePath);Directory.CreateDirectory(root);Refuses(()=>Engine.Extract(zip,root,progress,CancellationToken.None));
                Check(!Directory.EnumerateFileSystemEntries(root).Any(),"Duplicate validation was late");
            });
            Console.WriteLine("ALL "+passed+" BOOTSTRAP TESTS PASSED");return 0;
        } catch(Exception error) {Console.Error.WriteLine(error);return 1;}
    }
}
