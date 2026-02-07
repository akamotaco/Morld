
using System;
using Godot;
using ECS;
using System.Collections.Generic;

namespace SE
{
	public class World : ECS.ECS
	{
        public Node Root {get; private set;}

        public World(Node root)
		{
			this.Root = root;
		}

        public void Update(int deltaMs)
		{
			this.Step(deltaMs);
		}
    }
}
