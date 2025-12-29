// using System;
// using System.Runtime;
// using ECS;
// using Godot;

// namespace SE
// {
//     public class Unit : Entity
//     {
//         public Unit(GodotAsset godotAsset, Terrain terrain, Status? status)
//         {
//             if(godotAsset == null || terrain == null)
//                 GD.PrintErr("something is wrong");
//             if(status != null)
//                 this.AddComponent(status.Clone());
//             this.AddComponent(godotAsset);
//             this.AddComponent(new Movement(terrain));
//         }

//         internal override void OnCreate()
//         {
//             var asset = this.GetComponent<GodotAsset>();
//             var field = this.GetComponent<Movement>().Terrain;

//             if(asset == null)
//                 GD.PrintErr("asset is null");
//             if(asset.Node == null)
//                 asset.Create();
//                 // GD.PrintErr("asset Node is null");

//             if(asset.Node.GetParent() != null) {
//                 asset.Node.GetParent().RemoveChild(asset.Node);
//             }

//             if(field == null) {
//                 GD.Print("field is null");
//             }
//             field.Root.AddChild(asset.Node);

//             base.OnCreate();
//         }

//         internal override void OnDestory()
//         {
//             var asset = this.GetComponent<GodotAsset>();

//             if(asset.Node.GetParent() != null) {
//                 asset.Node.GetParent().RemoveChild(asset.Node);
//             }

//             base.OnDestory();
//         }

//         internal void UpdateTerrain(Terrain newField)
//         {
//             var asset = this.GetComponent<GodotAsset>();
//             // var field = this.GetComponent<Terrain>();
//             var field = this.GetComponent<Movement>().Terrain;
//             field.Root.RemoveChild(asset.Node);
//             newField.Root.AddChild(asset.Node);

//             this.GetComponent<Movement>().TerrainUpdate(newField);

//             // this.UpdateComponent(field, newField);
//             // field.CopyFrom(newField);
//             // this.DestroyComponent(field);
//             // this.AddComponent(newField);
//         }

//     }
// }