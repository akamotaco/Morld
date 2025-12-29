using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using Godot;

namespace SE
{
    public class SpriteInfo
    {
        public string name {get; private set;}
        public Texture2D texture {get; private set;}
        public int centerX {get; private set;}
        public int centerY {get; private set;}
        public int width {get; private set;}
        public int height {get; private set;}

        public SpriteInfo(string name, Texture2D texture, int centerX, int centerY)
        {
            this.name = name;
            this.texture = texture;
            this.centerX = centerX;
            this.centerY = centerY;
            this.width = this.texture.GetWidth();
            this.height = this.texture.GetHeight();
        }

        // internal void Apply(ref Sprite3D s3d, float scale=1, bool absolute=false)
        // {
        //     s3d.Texture = this.texture;
        //     s3d.Offset = new Vector2(centerX,centerY);
        //     s3d.PixelSize = absolute ? scale : 1.0f/height * scale;
        // }
    }

    public class SpriteAnimInfo
    {
        public string Name {get; private set;}
        public bool Loop {get; private set;}
        public (SpriteInfo si, int msecs)[] Animset {get; private set;}
        public int mSec {get; private set;}

        public SpriteAnimInfo(string name, bool loop, List<(SpriteInfo si, float secs)> animset)
        {
            this.Name = name;
            this.Loop = loop;
            this.Animset = new (SpriteInfo si, int msecs)[animset.Count];
            int sum = 0;
            for(int i=0;i<this.Animset.Length;++i) {
                // GD.Print($"{i}/{animset[i].secs}");
                var t = Math.Abs((int)(animset[i].secs*1000));
                this.Animset[i] = (animset[i].si, t);
                sum += t;
            }
            this.mSec = sum;
            // GD.Print($"sum/{sum}");
            if(this.mSec == 0)
                this.mSec = 1;
        }
    }

    public class spriteAnimBundle
    {
        public string Name {get;private set;}
        public List<SpriteAnimInfo> animSet {get; private set;}

        public spriteAnimBundle(string bundleName)
        {
            this.Name = bundleName;
            this.animSet = new List<SpriteAnimInfo>();
        }

        public SpriteAnimInfo Find(string animName)
        {
            return this.animSet.Find(x=>x.Name == animName);
        }

        internal void Add(SpriteAnimInfo sai)
        {
            this.animSet.Add(sai);
        }

        internal bool valid()
        {
            if(this.animSet.Count == 0)
                return false;
            return true;
        }
    }

    public class SpriteAnimInstance
    {
        internal int scale;
        internal float speed;
        internal int time;
        internal bool absolute;
        private spriteAnimBundle spriteAnimBundle;
        private int currentIndex = 0;

        public SpriteAnimInstance(spriteAnimBundle spriteAnimBundle)
        {
            this.spriteAnimBundle = spriteAnimBundle;
        }

        internal void Apply(ref Sprite3D s3d, int step)
        {
            if(this.spriteAnimBundle == null) return;

            // GD.Print(time);
            var currentAnim = this.spriteAnimBundle.animSet[currentIndex];
            if(time < currentAnim.mSec) {
                time += (int)(speed*step);
            }
            if(currentAnim.Loop == true && time >= currentAnim.mSec)
                time -= currentAnim.mSec;

            var check = time;
            int i=0;
            int count = currentAnim.Animset.Length;
            while(check>0 && i < count)
                check -= currentAnim.Animset[i++].msecs;

            var si = currentAnim.Animset[i%count].si;
            // GD.Print(si.name);
            {
                s3d.Texture = si.texture;
                s3d.Offset = new Vector2(si.centerX,si.centerY);
                s3d.PixelSize = absolute ? scale : 1.0f/si.height * scale;
            }
        }

        public int getIndexByName(string name)
        {
            for(int i=0;i<this.spriteAnimBundle.animSet.Count;++i)
            {
                if(this.spriteAnimBundle.animSet[i].Name == name)
                {
                    return i;
                }

            }

            return -1;
        }

        public bool setAnim(int index)
        {
            if(index < 0 || index >= this.spriteAnimBundle.animSet.Count)
                return false;

            this.currentIndex = index;
            return true;
        }
    }

    public class SpriteManager
    {
    #region singleton
        private static SpriteManager instance = null;
        private static readonly object padlock = new object();

        public static SpriteManager Instance
        {
            get
            {
                lock (padlock)
                {
                    if (instance == null)
                    {
                        instance = new SpriteManager();
                    }
                    return instance;
                }
            }
        }
    #endregion
        List<SpriteInfo> spriteBundle = new List<SpriteInfo>();
        List<spriteAnimBundle> spriteAnimBundle = new List<spriteAnimBundle>();

        internal void LoadSpriteCSV(string csvfilename)
        {
            var tempImageDict = new Dictionary<string, Image>();
            var lines = GameUtil.readCsvLines(csvfilename);

            if(lines == null) {
                GD.PrintErr($"LoadSpriteCSV failed. path:{csvfilename}");
                return;
            }
            

            GD.Print("loadcsv:sprite:"+lines.Length);

            foreach(var line in lines)
            {
                if(line.Length == 0 || line[0][0] == '#')
                    continue;

                {
                    var name = line[0].Trim();
                    var filename = line[1].Trim();
                    var pxX = int.Parse(line[2]);
                    var pxY = int.Parse(line[3]);
                    var width = int.Parse(line[4]);
                    var height = int.Parse(line[5]);
                    var centerX = int.Parse(line[6]);
                    var centerY = int.Parse(line[7]);

                    if(tempImageDict.ContainsKey(filename) == false) {
                        var namesize = System.IO.Path.GetFileName(csvfilename);
                        var srcPath = csvfilename.Substring(0,csvfilename.Length-namesize.Length);
                        // GD.Print("src:"+srcPath+filename);
                        var newImg = Image.LoadFromFile(srcPath+filename);
                        // GD.PrintT(newImg);
                        tempImageDict[filename] = newImg;
                    }
                    var img = tempImageDict[filename];
                    var subImg = Image.Create(width, height, false, Image.Format.Rgba8);
                    subImg.BlitRect(img, new Rect2I(pxX, pxY, width, height), new Vector2I());

                    var tex = ImageTexture.CreateFromImage(subImg);
                    SpriteInfo si = new SpriteInfo(name,tex,centerX,centerY);

                    if(this.spriteBundle.Find(x=>x.name == name) != null)
                        throw new System.Exception("already has key:"+name);

                    // GD.Print("before:"+this.spriteBundle.Count);
                    this.spriteBundle.Add(si);
                    // GD.Print("after:"+this.spriteBundle.Count);
                    GD.Print("loadcsv:sprite:name:"+name);
                }
            }
        }

        public SpriteInfo FindSpriteByName(string name)
        {
            return this.spriteBundle.Find(x=>x.name == name);
        }

        internal void LoadAnimCSV(string csvfilename)
        {
            var lines = GameUtil.readCsvLines(csvfilename);

            if(lines == null) {
                GD.PrintErr($"LoadAnimCSV failed. path:{csvfilename}");
                return;
            }

            GD.Print("loadcsv:anim:"+lines.Length);

            foreach(var line in lines)
            {
                if(line.Length == 0 || line[0][0] == '#')
                    continue;

                {
                    var bundleName = line[0].Trim();
                    var animName = line[1].Trim();
                    var loop = bool.Parse(line[2].Trim());
                    var currentBundle = this.FindBundleByName(bundleName);

                    if(currentBundle == null)
                        currentBundle = new spriteAnimBundle(bundleName);
                        this.spriteAnimBundle.Add(currentBundle);
                    
                    if(currentBundle.Find(animName) != null)
                        throw new Exception("duplicated anim:" + animName + "in bundle("+currentBundle.Name+")" );

                    var animSet = new List<(SpriteInfo si, float secs)>();
                    for(var i=3;i<line.Length;i+=2) {
                        var spriteName = line[i].Trim();
                        var secs = float.Parse(line[i+1]);
                        var sprite = FindSpriteByName(spriteName);
                        if(sprite == null)
                            throw new System.Exception("sprite is null:"+spriteName);
                        animSet.Add((sprite, secs));
                    }

                    var sai = new SpriteAnimInfo(animName, loop, animSet);
                    currentBundle.Add(sai);
                    // this.spriteAnimBundle.Add(sai);

                    GD.Print("loadcsv:anim:name:"+animName);
                }
            }
        }

        public spriteAnimBundle FindBundleByName(string name)
        {
            return this.spriteAnimBundle.Find(x=>x.Name == name);
        }
    }
}