// Small Windows bootstrapper. Requires only Windows' .NET Framework 4.8.
// ReleaseSpec is generated at build time from the exact payload SHA-256.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace SuryadevSetup {
    public sealed class Payload {
        public string Url, Hash, ExeHash, Version;
        public long Bytes;
        public Payload(string url, string hash, string exeHash, long bytes, string version) {
            Url=url; Hash=hash; ExeHash=exeHash; Bytes=bytes; Version=version;
        }
    }
    public sealed class Receipt {
        public string Schema="suryadev.small-setup.v1";
        public string Version, Exe, Data, PackageSha256, ComponentState;
        public bool ComponentsSkipped, Paired=false;
    }
    public static class Engine {
        public const string Marker="suryadev-install.json";
        public static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
        public static string HashFile(string path) {
            using(var input=File.OpenRead(path)) using(var hash=SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        }
        public static string Quote(string text) {
            // Windows CommandLineToArgvW quoting, including trailing backslashes.
            if(text.IndexOf('\0')>=0) throw new ArgumentException("Invalid argument");
            var result=new System.Text.StringBuilder("\""); int slashes=0;
            foreach(char ch in text) {
                if(ch=='\\') {slashes++;continue;}
                if(ch=='\"') {result.Append('\\',slashes*2+1);result.Append(ch);}
                else {result.Append('\\',slashes);result.Append(ch);}
                slashes=0;
            }
            result.Append('\\',slashes*2);result.Append('"');return result.ToString();
        }
        public static Uri ValidateUrl(string source) {
            Uri uri;
            if(!Uri.TryCreate(source,UriKind.Absolute,out uri) || !String.IsNullOrEmpty(uri.UserInfo)
                || !String.IsNullOrEmpty(uri.Query) || !String.IsNullOrEmpty(uri.Fragment))
                throw new InvalidOperationException("Use an HTTPS package URL, or a private LAN HTTP URL, without credentials or query parameters.");
            IPAddress ip;
            bool local=IPAddress.TryParse(uri.Host,out ip) && ip.AddressFamily==AddressFamily.InterNetwork
                && (ip.GetAddressBytes()[0]==10 || ip.GetAddressBytes()[0]==127
                || (ip.GetAddressBytes()[0]==192 && ip.GetAddressBytes()[1]==168)
                || (ip.GetAddressBytes()[0]==172 && ip.GetAddressBytes()[1]>=16 && ip.GetAddressBytes()[1]<=31));
            if(uri.Scheme!=Uri.UriSchemeHttps && !(uri.Scheme==Uri.UriSchemeHttp && local))
                throw new InvalidOperationException("Internet downloads require HTTPS. HTTP is accepted only for an explicit private LAN address; the pinned package checksum still applies.");
            return uri;
        }
        public static void NoReparseParents(string path) {
            var current=new DirectoryInfo(Path.GetFullPath(path));
            while(current!=null) {
                if(current.Exists && (current.Attributes&FileAttributes.ReparsePoint)!=0)
                    throw new InvalidOperationException("Choose an installation path without symbolic links or junctions.");
                current=current.Parent;
            }
        }
        public static string ValidateRoot(string path) {
            string root=Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
            if(root.Length>85 || root.Length<4 || root==Path.GetPathRoot(root).TrimEnd('\\')
                || root.StartsWith(@"\\",StringComparison.Ordinal))
                throw new InvalidOperationException("Choose a short local installation folder (up to 85 characters), not a drive root or network share.");
            NoReparseParents(root);
            if(File.Exists(root)) throw new InvalidOperationException("The installation location is a file.");
            string marker=Path.Combine(root,Marker);
            if(Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any()) {
                if(!File.Exists(marker) || new FileInfo(marker).Length>16384)
                    throw new InvalidOperationException("This folder contains other files. Choose an empty folder or a marked SURYADEV setup folder. Nothing was overwritten.");
                var saved=Json.Deserialize<Receipt>(File.ReadAllText(marker));
                if(saved==null || saved.Schema!="suryadev.small-setup.v1")
                    throw new InvalidOperationException("Unrecognized installation marker. Nothing was changed.");
            }
            return root;
        }
        public static void Save(string root, Receipt receipt) {
            string path=Path.Combine(root,Marker), temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
            File.WriteAllText(temp,Json.Serialize(receipt));
            if(File.Exists(path)) File.Replace(temp,path,path+".previous");
            else File.Move(temp,path);
        }
        public static void Download(Uri uri,string destination,Payload spec,Action<string,int> progress,CancellationToken cancel) {
            // Redirects are inspected manually: HTTPS can never downgrade.
            Uri current=uri;
            for(int hop=0;hop<8;hop++) {
                cancel.ThrowIfCancellationRequested();
                var request=(HttpWebRequest)WebRequest.Create(current);
                request.UserAgent="SURYADEV-Small-Setup/1.0";
                request.AllowAutoRedirect=false;
                request.Timeout=30000; request.ReadWriteTimeout=60000;
                using(cancel.Register(()=>request.Abort()))
                using(var response=(HttpWebResponse)request.GetResponse()) {
                    int code=(int)response.StatusCode;
                    if(code>=300 && code<400) {
                        var next=new Uri(current,response.Headers["Location"]);
                        if(next.Scheme!=Uri.UriSchemeHttps && !(uri.Scheme=="http" && next.Scheme=="http" && next.Host==uri.Host && next.Port==uri.Port))
                            throw new InvalidOperationException("Unsafe download redirect refused.");
                        if(!String.IsNullOrEmpty(next.UserInfo)) throw new InvalidOperationException("Credential-bearing redirect refused.");
                        current=next; continue;
                    }
                    if(response.ContentLength>0 && response.ContentLength!=spec.Bytes)
                        throw new InvalidDataException("The download size does not match this setup release.");
                    long total=0; var buffer=new byte[131072];
                    using(var input=response.GetResponseStream())
                    using(var output=new FileStream(destination,FileMode.Create,FileAccess.Write,FileShare.None)) {
                        int count;
                        while((count=input.Read(buffer,0,buffer.Length))>0) {
                            cancel.ThrowIfCancellationRequested(); total+=count;
                            if(total>spec.Bytes) throw new InvalidDataException("Download exceeds the pinned package size.");
                            output.Write(buffer,0,count);
                            progress("Downloading Learner: "+(total/1048576)+" / "+(spec.Bytes/1048576)+" MiB",(int)Math.Min(55,55*total/spec.Bytes));
                        }
                    }
                    if(total!=spec.Bytes || HashFile(destination)!=spec.Hash.ToLowerInvariant())
                        throw new InvalidDataException("Package checksum mismatch. Nothing downloaded will be executed.");
                    return;
                }
            }
            throw new InvalidOperationException("Too many download redirects.");
        }
        public static void Extract(string zipPath,string destination,Action<string,int> progress,CancellationToken cancel) {
            string root=Path.GetFullPath(destination).TrimEnd('\\')+"\\";
            long total=0;
            var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            using(var zip=ZipFile.OpenRead(zipPath)) {
                if(zip.Entries.Count>15000) throw new InvalidDataException("Unexpected package entry count.");
                // Validate the WHOLE archive before writing its first file.
                foreach(var entry in zip.Entries) {
                    string name=entry.FullName.Replace('\\','/');
                    if(!name.StartsWith("Suryadev-Learner/",StringComparison.Ordinal)
                        || name.Split('/').Any(p=>p==".." || p=="." || p.Contains(":"))
                        || (entry.ExternalAttributes>>16 & 0xF000)==0xA000)
                        throw new InvalidDataException("Unsafe archive path or symbolic link.");
                    name=name.Substring("Suryadev-Learner/".Length);
                    if(name.Length==0) continue;
                    string target=Path.GetFullPath(Path.Combine(root,name.Replace('/', '\\')));
                    if(!target.StartsWith(root,StringComparison.OrdinalIgnoreCase) || target.Length>=255
                        || !names.Add(target)) throw new InvalidDataException("Unsafe, duplicate or overlong archive path.");
                    total+=entry.Length;
                    if(total>12L*1024*1024*1024 || entry.Length>4L*1024*1024*1024)
                        throw new InvalidDataException("Archive expansion limit exceeded.");
                }
                int done=0;
                foreach(var entry in zip.Entries) {
                    cancel.ThrowIfCancellationRequested();
                    string name=entry.FullName.Replace('\\','/').Substring("Suryadev-Learner/".Length);
                    if(name.Length==0) continue;
                    string target=Path.GetFullPath(Path.Combine(root,name.Replace('/','\\')));
                    if(name.EndsWith("/")) Directory.CreateDirectory(target);
                    else {
                        Directory.CreateDirectory(Path.GetDirectoryName(target));
                        using(var input=entry.Open()) using(var output=new FileStream(target,FileMode.CreateNew,FileAccess.Write)) input.CopyTo(output);
                    }
                    progress("Installing verified app files",55+(int)(25L*++done/zip.Entries.Count));
                }
            }
        }
        public static int Run(string exe,string arguments,Action<string,int> progress,int timeoutSeconds,bool allowDeferred=false) {
            var start=new ProcessStartInfo(exe,arguments) {UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
            start.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";
            string error="";
            using(var process=new Process {StartInfo=start}) {
                process.OutputDataReceived+=(s,e)=> {
                    if(e.Data==null) return;
                    if(e.Data.StartsWith("SURYADEV_SETUP ")) {
                        try { var state=Json.Deserialize<Dictionary<string,object>>(e.Data.Substring(15)); progress(Convert.ToString(state["note"]),90); } catch { }
                    }
                };
                process.ErrorDataReceived+=(s,e)=> {if(e.Data!=null) error=(error+e.Data+"\n").Substring(Math.Max(0,(error+e.Data+"\n").Length-2000));};
                process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
                if(!process.WaitForExit(timeoutSeconds*1000))
                    throw new InvalidOperationException("The setup helper is still running. No unrelated process was stopped. Close it before retrying.");
                process.WaitForExit();
                if(process.ExitCode!=0 && !(allowDeferred && process.ExitCode==10))
                    throw new InvalidOperationException("Local component or runtime verification failed (exit "+process.ExitCode+"). "+error);
                return process.ExitCode;
            }
        }
        public static Receipt Install(string requested,string source,Payload spec,bool skipComponents,Action<string,int> progress,CancellationToken cancel) {
            string root=ValidateRoot(requested);
            var drive=new DriveInfo(Path.GetPathRoot(root));
            if(drive.AvailableFreeSpace<12L*1024*1024*1024)
                throw new InvalidOperationException("Setup needs at least 12 GiB free disk space for the app, download cache and local components.");
            Directory.CreateDirectory(root);
            // Hold a real cross-process lock through download, extraction and setup.
            using(var installLock=new FileStream(Path.Combine(root,".setup.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)) {
                Receipt previous=File.Exists(Path.Combine(root,Marker)) ? Json.Deserialize<Receipt>(File.ReadAllText(Path.Combine(root,Marker))) : new Receipt();
                if(!File.Exists(Path.Combine(root,Marker))) Save(root,previous);
                Directory.CreateDirectory(Path.Combine(root,"cache"));
                Directory.CreateDirectory(Path.Combine(root,"versions"));
                string cached=Path.Combine(root,"cache",spec.Hash+".zip");
                if(!File.Exists(cached) || new FileInfo(cached).Length!=spec.Bytes || HashFile(cached)!=spec.Hash.ToLowerInvariant()) {
                    string partial=cached+".partial";
                    Exception last=null;
                    for(int attempt=0;attempt<3;attempt++) {
                        try { Download(ValidateUrl(source),partial,spec,progress,cancel); last=null; break; }
                        catch(OperationCanceledException) {throw;}
                        catch(Exception e) { if(cancel.IsCancellationRequested) throw new OperationCanceledException(); last=e; progress("Download interrupted; retry "+(attempt+1)+" of 3. "+e.Message,0); if(attempt<2) cancel.WaitHandle.WaitOne(1000*(attempt+1)); }
                    }
                    if(last!=null) throw last;
                    if(File.Exists(cached)) File.Move(cached,cached+".invalid-"+Guid.NewGuid().ToString("N"));
                    File.Move(partial,cached);
                } else progress("Reusing checksum-verified download",55);
                string version=Path.Combine(root,"versions",spec.Hash.Substring(0,12));
                if(!Directory.Exists(version)) {
                    string stage=version+".staging-"+Guid.NewGuid().ToString("N").Substring(0,8);
                    Directory.CreateDirectory(stage);
                    Extract(cached,stage,progress,cancel);
                    if(HashFile(Path.Combine(stage,"Suryadev-Learner.exe"))!=spec.ExeHash.ToLowerInvariant())
                        throw new InvalidDataException("The installed EXE does not match this release.");
                    Run(Path.Combine(stage,"Suryadev-Learner.exe"),"--self-test",progress,90);
                    Directory.Move(stage,version);
                }
                cancel.ThrowIfCancellationRequested();
                string exe=Path.Combine(version,"Suryadev-Learner.exe"), data=Path.Combine(root,"data");
                if(HashFile(exe)!=spec.ExeHash.ToLowerInvariant()) throw new InvalidDataException("Existing version EXE has changed; use a new empty installation folder.");
                progress("Checking the installed Learner backend",82);
                Run(exe,"--self-test",progress,90);
                progress("Preparing free local components; downloads may take several minutes",85);
                int code=skipComponents ? -1 : Run(exe,"--setup-components --data "+Quote(data),progress,3600,true);
                var receipt=new Receipt {Version=spec.Version, Exe=exe, Data=data,PackageSha256=spec.Hash,
                    ComponentState=skipComponents?"test_skipped":code==10?"deferred_hardware":"ready",ComponentsSkipped=skipComponents};
                // Only publish a new active version after it passes verification.
                Save(root,receipt);
                progress(code==10 ? "App installed. Local model setup is waiting for safe hardware; evidence collection remains available." : skipComponents ? "App installed; components explicitly skipped for this test." : "App and local components ready. Secure KRISHNA pairing is next.",100);
                return receipt;
            }
        }
        public static string LaunchArgs(Receipt receipt,int port) {
            return "--data "+Quote(receipt.Data)+" --model auto --auto-setup --fast-books --adaptive-fleet --continuous --auto-approved-videos "+
                (File.Exists(Path.Combine(receipt.Data,"video-trial-selection.json"))?"":"--video-target 5 ")+
                "--pdf-target 10 --book-target 5 --max-parallel 25 --port "+port;
        }
        public static void Launch(Receipt receipt,int port,bool pairing) {
            // Never take over another installation or dashboard already using this port.
            using(var socket=new TcpClient()) {
                try { if(socket.ConnectAsync("127.0.0.1",port).Wait(400) && socket.Connected)
                    throw new InvalidOperationException("Dashboard port "+port+" is already in use. Close the other dashboard or choose another port."); }
                catch(AggregateException) { }
            }
            var start=new ProcessStartInfo(receipt.Exe,LaunchArgs(receipt,port)) {UseShellExecute=false,CreateNoWindow=true};
            start.EnvironmentVariables["SURYADEV_AUTO_SETUP"]="1";
            Process.Start(start);
            Task.Run(()=> {
                for(int i=0;i<30;i++) {
                    try { using(var client=new WebClient()) {
                        client.Proxy=null;
                        string raw=client.DownloadString("http://127.0.0.1:"+port+"/api/learning/control");
                        var control=Json.Deserialize<Dictionary<string,object>>(raw);
                        if(!String.Equals(Convert.ToString(control["workspace_data_dir"]).TrimEnd('\\'),receipt.Data.TrimEnd('\\'),StringComparison.OrdinalIgnoreCase)) return;
                        Process.Start("http://127.0.0.1:"+port+"/advanced#"+(pairing?"server-settings":"ai-learner")); return;
                    }} catch { Thread.Sleep(1000); }
                }
            });
        }
        public static void Shortcut(Receipt receipt,int port) {
            var type=Type.GetTypeFromProgID("WScript.Shell");
            dynamic shell=Activator.CreateInstance(type);
            string path=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"SURYADEV AI Learner.lnk");
            dynamic link=shell.CreateShortcut(path);
            string versions=Path.Combine(Directory.GetParent(receipt.Data).FullName,"versions")+"\\";
            if(File.Exists(path) && !Convert.ToString(link.TargetPath).StartsWith(versions,StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("A shortcut for a different installation already exists; it was preserved.");
            link.TargetPath=receipt.Exe; link.Arguments=LaunchArgs(receipt,port);
            link.WorkingDirectory=Path.GetDirectoryName(receipt.Exe); link.WindowStyle=7;
            link.Description="SURYADEV local AI Learner - hardware adaptive, secure KRISHNA pairing";
            link.Save();
        }
    }
    public sealed class SetupWindow : Form {
        TextBox path=new TextBox(), mirror=new TextBox(), log=new TextBox();
        NumericUpDown port=new NumericUpDown();
        Button install=new Button(), cancel=new Button(), open=new Button();
        ProgressBar bar=new ProgressBar(); CheckBox desktop=new CheckBox();
        CancellationTokenSource cancellation; bool running; Receipt receipt;
        public SetupWindow(string initial) {
            Text="SURYADEV Setup"; Size=new Size(720,570); MinimumSize=Size;
            StartPosition=FormStartPosition.CenterScreen; Font=new Font("Segoe UI",10);
            var title=new Label {Text="Install SURYADEV AI Learner",Font=new Font("Segoe UI",18,FontStyle.Bold),AutoSize=true,Location=new Point(22,18)};
            Controls.Add(title);
            Controls.Add(new Label {Text="1  Choose folder    2  Download & verify    3  Local components    4  Secure pairing",AutoSize=true,Location=new Point(24,65)});
            Controls.Add(new Label {Text="Installation folder",AutoSize=true,Location=new Point(24,105)});
            path.SetBounds(24,130,560,29); path.Text=initial;
            var browse=new Button {Text="Browse",Location=new Point(590,128),Size=new Size(90,31)};
            browse.Click+=(s,e)=> {using(var dialog=new FolderBrowserDialog {SelectedPath=path.Text,Description="Choose an empty local SURYADEV installation folder"}) if(dialog.ShowDialog()==DialogResult.OK) path.Text=dialog.SelectedPath;};
            Controls.Add(path);Controls.Add(browse);
            Controls.Add(new Label {Text="Optional LAN mirror package URL (leave blank for the official download)",AutoSize=true,Location=new Point(24,173)});
            mirror.SetBounds(24,197,656,29); Controls.Add(mirror);
            Controls.Add(new Label {Text="Dashboard port",AutoSize=true,Location=new Point(24,245)});
            port.SetBounds(146,242,90,28); port.Minimum=1024;port.Maximum=65535;port.Value=8872; Controls.Add(port);
            desktop.Text="Create desktop shortcut";desktop.Checked=true;desktop.SetBounds(290,242,300,30);Controls.Add(desktop);
            bar.SetBounds(24,287,656,22); Controls.Add(bar);
            log.SetBounds(24,323,656,130);log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;Controls.Add(log);
            log.Text="The setup EXE is small. The full Learner and missing local components download over your current Wi-Fi/Ethernet connection. Existing learning data is preserved. KRISHNA pairing requires owner approval.";
            install.Text="Install";install.SetBounds(24,473,110,35);Controls.Add(install);
            cancel.Text="Cancel";cancel.Enabled=false;cancel.SetBounds(144,473,110,35);Controls.Add(cancel);
            open.Text="Open secure pairing";open.Enabled=false;open.SetBounds(460,473,220,35);Controls.Add(open);
            install.Click+=async(s,e)=> {
                running=true;install.Enabled=false;cancel.Enabled=true;open.Enabled=false;
                path.Enabled=false;mirror.Enabled=false;browse.Enabled=false;
                cancellation=new CancellationTokenSource();
                try {
                    string root=path.Text, source=String.IsNullOrWhiteSpace(mirror.Text)?ReleaseSpec.Url:mirror.Text.Trim();
                    receipt=await Task.Run(()=>Engine.Install(root,source,ReleaseSpec.Payload,false,Report,cancellation.Token));
                    if(desktop.Checked) {try {Engine.Shortcut(receipt,(int)port.Value);} catch(Exception error) {Report("App installed; shortcut could not be created: "+error.Message,100);}}
                    open.Enabled=true;
                } catch(OperationCanceledException) {Report("Cancelled safely. Existing learning data and installed versions are retained. Retry to continue.",0);}
                catch(Exception error) {Report("Setup did not complete: "+error.Message,0);MessageBox.Show(this,error.Message,"SURYADEV setup",MessageBoxButtons.OK,MessageBoxIcon.Information);}
                finally {running=false;install.Enabled=true;cancel.Enabled=false;path.Enabled=true;mirror.Enabled=true;browse.Enabled=true;}
            };
            cancel.Click+=(s,e)=>{cancellation.Cancel();Report("Cancelling download. A running component installer is allowed to finish safely.",bar.Value);};
            open.Click+=(s,e)=>{try {Engine.Launch(receipt,(int)port.Value,true);}catch(Exception error){MessageBox.Show(this,error.Message,"SURYADEV");}};
            FormClosing+=(s,e)=>{if(running){e.Cancel=true;cancellation.Cancel();Report("Wait for the current operation to finish safely before closing.",bar.Value);}};
        }
        void Report(string message,int percent) {
            if(InvokeRequired) {BeginInvoke((Action)(()=>Report(message,percent)));return;}
            bar.Value=Math.Max(0,Math.Min(100,percent));
            // Replace repeated transfer/extraction progress instead of growing logs indefinitely.
            if(message.StartsWith("Downloading Learner:") || message=="Installing verified app files") {
                var lines=log.Lines;
                if(lines.Length>0 && (lines.Last().StartsWith("Downloading Learner:") || lines.Last()=="Installing verified app files"))
                    log.Lines=lines.Take(lines.Length-1).Concat(new[]{message}).ToArray();
                else log.AppendText(Environment.NewLine+message);
            } else log.AppendText(Environment.NewLine+message);
            log.SelectionStart=log.Text.Length;log.ScrollToCaret();
        }
    }
    static class Program {
        [STAThread] static int Main(string[] args) {
            ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
            try {
                if(args.Contains("--headless")) {
                    Func<string,string,string> option=(name,fallback)=> {int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:fallback;};
                    string root=option("--install-dir",null); if(root==null) throw new ArgumentException("--install-dir is required in headless mode");
                    var receipt=Engine.Install(root,option("--source",ReleaseSpec.Url),ReleaseSpec.Payload,args.Contains("--skip-components"),(s,p)=>Console.WriteLine(p+"% "+s),CancellationToken.None);
                    File.WriteAllText(Path.Combine(root,"setup-result.json"),Engine.Json.Serialize(receipt));
                    return receipt.ComponentsSkipped?20:receipt.ComponentState=="ready"?0:10;
                }
                Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
                string initial=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"SURYADEV");
                int index=Array.IndexOf(args,"--install-dir");if(index>=0 && index+1<args.Length) initial=args[index+1];
                Application.Run(new SetupWindow(initial));return 0;
            } catch(Exception error) {Console.Error.WriteLine("SURYADEV SETUP: "+error.Message);return 2;}
        }
    }
}
