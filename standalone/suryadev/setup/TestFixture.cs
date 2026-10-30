using System;
using System.IO;
static class Fixture {
    static int Main(string[] args) {
        string log=Environment.GetEnvironmentVariable("SURYADEV_TEST_EXECUTIONS");
        if(log!=null) File.AppendAllText(log,String.Join("|",args)+Environment.NewLine);
        if(args.Length>0 && args[0]=="--setup-components") {
            int index=Array.IndexOf(args,"--data");
            if(index<0 || index+1>=args.Length) return 2;
            Directory.CreateDirectory(args[index+1]);
            Console.WriteLine("SURYADEV_SETUP {\"state\":\"ready\",\"note\":\"Test fixture only\"}");
        }
        return 0;
    }
}
