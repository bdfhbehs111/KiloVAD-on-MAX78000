using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using ATK_UT70DLL;

// UT70 capture tool: connects, sets sample rate, logs every sample to CSV,
// and prints an energy summary. Usage: ut70cap.exe <seconds> <out.csv> [sps]
class Program
{
    static long n = 0;
    static double sumV = 0, sumI = 0, sumP = 0;
    static double maxI = double.MinValue, minI = double.MaxValue;
    static double wh0 = -1, wh1 = 0, ah0 = -1, ah1 = 0;
    static StreamWriter w;
    static readonly StringBuilder sb = new StringBuilder(4096);
    static readonly object lk = new object();

    static void OnData(List<CVDataModel> list)
    {
        if (list == null) return;
        lock (lk)
        {
            for (int k = 0; k < list.Count; k++)
            {
                CVDataModel d = list[k];
                n++;
                sumV += d.V; sumI += d.I; sumP += d.P;
                if (d.I > maxI) maxI = d.I;
                if (d.I < minI) minI = d.I;
                if (wh0 < 0) { wh0 = d.Wh; ah0 = d.AH; }
                wh1 = d.Wh; ah1 = d.AH;
                if (w != null)
                    sb.Append(ElapsedMs()).Append(',').Append(F(d.V)).Append(',').Append(F(d.I))
                      .Append(',').Append(F(d.P)).Append(',').Append(F(d.Dp)).Append(',').Append(F(d.Dm))
                      .Append(',').Append(F(d.R)).Append(',').Append(F(d.Wh)).Append(',').Append(F(d.AH))
                      .AppendLine();
            }
        }
    }

    static string F(float v) { return v.ToString("0.######", CultureInfo.InvariantCulture); }

    static System.Diagnostics.Stopwatch sw;
    static double ElapsedMs() { return sw.Elapsed.TotalMilliseconds; }

    static void Main(string[] args)
    {
        int secs = args.Length > 0 ? int.Parse(args[0]) : 10;
        string csv = args.Length > 1 ? args[1] : "ut70_raw.csv";
        int sps = args.Length > 2 ? int.Parse(args[2]) : 1000;

        Frequency freq = Frequency._1000SPS;
        switch (sps)
        {
            case 4: freq = Frequency._4SPS; break;
            case 10: freq = Frequency._10SPS; break;
            case 50: freq = Frequency._50SPS; break;
            case 200: freq = Frequency._200SPS; break;
            case 500: freq = Frequency._500SPS; break;
            default: freq = Frequency._1000SPS; break;
        }

        ATKUT70 dev = new ATKUT70();
        dev.ReceCVDataEvent += OnData;
        dev.FrequencyEvent += delegate(Frequency f) { Console.WriteLine("[evt] frequency = " + f); };
        dev.DevSNEvent += delegate(byte hw, string sn) { Console.WriteLine("[evt] hw=" + hw + " sn=" + sn); };

        Console.WriteLine("ConnDev()  -> " + dev.ConnDev());
        Console.WriteLine("ConnState  -> " + dev.ConnState);
        dev.GetDevVer();
        dev.GetFrequency();
        Thread.Sleep(400);

        dev.SetFrequency(freq);
        Thread.Sleep(300);
        dev.ResteAH();
        Thread.Sleep(300);

        w = new StreamWriter(csv, false, new UTF8Encoding(false));
        w.WriteLine("t_ms,V,I,P,Dp,Dm,R,Wh,AH");
        sw = System.Diagnostics.Stopwatch.StartNew();

        Console.WriteLine("capturing " + secs + " s at " + sps + " SPS ...");
        for (int t = 0; t < secs; t++)
        {
            Thread.Sleep(1000);
            lock (lk) { if (sb.Length > 0) { w.Write(sb.ToString()); sb.Clear(); } }
            w.Flush();
            Console.Write("\r  t=" + (t + 1) + "s samples=" + n + " I=" + AvgI().ToString("0.0000") + "A P=" + AvgP().ToString("0.0000") + "W   ");
        }
        Console.WriteLine();

        dev.Disconnect();
        lock (lk) { if (sb.Length > 0) { w.Write(sb.ToString()); sb.Clear(); } }
        w.Flush(); w.Close();

        double dt = sw.Elapsed.TotalSeconds;
        Console.WriteLine();
        Console.WriteLine("========== SUMMARY ==========");
        Console.WriteLine("duration_s   = " + dt.ToString("0.00"));
        Console.WriteLine("samples      = " + n);
        Console.WriteLine("sample_rate  = " + (n / dt).ToString("0.0") + " /s");
        if (n > 0)
        {
            Console.WriteLine("mean_V       = " + (sumV / n).ToString("0.00000") + " V");
            Console.WriteLine("mean_I       = " + (sumI / n).ToString("0.00000") + " A");
            Console.WriteLine("mean_P       = " + (sumP / n).ToString("0.00000") + " W");
            Console.WriteLine("min_I        = " + minI.ToString("0.00000") + " A");
            Console.WriteLine("max_I        = " + maxI.ToString("0.00000") + " A");
            Console.WriteLine("energy_Wh    = " + (wh1 - wh0).ToString("0.000000") + " Wh (device counter)");
            Console.WriteLine("charge_Ah    = " + (ah1 - ah0).ToString("0.000000") + " Ah (device counter)");
            Console.WriteLine("energy_J     = " + ((wh1 - wh0) * 3600.0).ToString("0.000") + " J");
            Console.WriteLine("csv          = " + csv);
        }
        else
        {
            Console.WriteLine("!! no samples received");
        }
    }

    static double AvgI() { lock (lk) { return n > 0 ? sumI / n : 0; } }
    static double AvgP() { lock (lk) { return n > 0 ? sumP / n : 0; } }
}
