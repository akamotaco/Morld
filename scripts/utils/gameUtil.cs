using System.Collections.Generic;
using System;
using Godot;

namespace SE
{
    static public class GameUtil
    {
        static public string[][] readCsvLines(string filename)
        {
            try
            {
                var res = new List<string[]>();
                var f = Godot.FileAccess.Open(filename, Godot.FileAccess.ModeFlags.Read);

                if(f == null)
                    throw new Exception($"[Err:readCsvLines] read failed ({filename})");

                while(f.EofReached() == false)
                    res.Add(f.GetCsvLine());
                
                f.Close();

                return res.ToArray();
            }
            catch(Exception e)
            {
                GD.PrintErr("[Err:readCsvLines]:"+e);
                return null;
            }
        }

        static public string readTextFile(string filename)
        {
            try
            {
                var f = Godot.FileAccess.Open(filename, Godot.FileAccess.ModeFlags.Read);
                if(f == null)
                    throw new Exception($"[Err:readCsvLines] read failed ({filename})");
                    
                string res = f.GetAsText();

                f.Close();
                return res;
            }
            catch(Exception e)
            {
                GD.PrintErr("[Err:readTextFile]:"+e);
                return null;
            }
        }
    }
}