using System;
using System.Runtime.CompilerServices;
using ECS;
using Godot;

namespace SE
{
    public class GodotAsset : Component
	{
        public Node Node {get; private set;} = null;
        private PackedScene _scene;

        public GodotAsset(PackedScene scene)
		{
            this._scene = scene;
			this.Node = scene.Instantiate<Node3D>();
		}

        public GodotAsset(Node3D node3d)
        {
            this.Node = node3d;
        }

        public override void Create()
        {
            if(this.Node == null)
                this.Node = this._scene.Instantiate<Node3D>();
        }

        public override void Destroy()
        {
            if(this.Node != null) {
                this.Node.QueueFree();
            }
            this.Node = null;
        }

        internal void UpdateAsset(PackedScene scene)
        {
            var parent = this.Node.GetParent();
            Destroy();
            this.Node = scene.Instantiate<Node3D>();
            parent.AddChild(this.Node);
        }

        public static GodotAsset Instantiate(PackedScene scene)
		{
			return new GodotAsset(scene.Instantiate<Node3D>());
		}
    }
}