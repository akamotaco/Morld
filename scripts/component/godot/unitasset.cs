using Godot;

namespace SE
{
    public class SpriteAsset : GodotAsset
    {
        public SpriteAnimInstance anim = new SpriteAnimInstance(null); // ???

        public Sprite3D s3d;
        private BaseMaterial3D.BillboardModeEnum billboardMode;
        private Texture2D singleImage = null;
        private Vector3 singleImageScale;

        public SpriteAsset(PackedScene scene, BaseMaterial3D.BillboardModeEnum billboardMode=BaseMaterial3D.BillboardModeEnum.FixedY) : base(scene) {
            s3d = this.Node.FindChild("Sprite") as Sprite3D;
            this.billboardMode = billboardMode;
            SetBillboard(billboardMode);
        }

        public override void Create()
        {
            base.Create();
            if(this.singleImage != null) {
                s3d = this.Node.FindChild("Sprite") as Sprite3D;
                this.s3d.Texture = this.singleImage;
                this.s3d.Scale = this.singleImageScale;
            }
            SetBillboard(this.billboardMode);
        }

        internal void Texture2DOverride(Texture2D texture2D, Vector3? scale)
        {
            this.singleImage = texture2D;
            this.s3d.Texture = texture2D;
            if(scale != null) {
                this.s3d.Scale = scale.Value;
                this.singleImageScale = scale.Value;
            }
        }

        private bool SetBillboard(BaseMaterial3D.BillboardModeEnum billboardMode) {
            var sprite = this.Node.FindChild("Sprite") as Sprite3D;
            if(sprite == null) return false;
            
            sprite.Billboard = billboardMode;
            return true;
        }
    }
}