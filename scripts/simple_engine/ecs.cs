using System;
using System.Collections.Generic;
using Godot;
using SE;

namespace ECS
{
	public static class GUID {
		private static int ID;
		public static int GetUID()
		{
			ID++;
			return ID;
		}
	}

    public class Entity
    {
		public int Id {get; private set;}
        public bool Update {get; private set;} = true;
        public void Updated() {this.Update = true;}
        public void ReleaseUpdated(ECS ecs) {this.Update = false;} // ecs는 아무나 실행하지 않기 위한 필터링 개념. 실제로 기능하진 않음

        protected List<Component> _collection;

        public Entity() {
			this.Id = GUID.GetUID();
            _collection = new List<Component>();
        }

		public Component AddComponent(Component component) {
			this._collection.Add(component);
			component.Entity = this;
            return component;
		}

        public bool RemoveComponent(Component component) {
            if(this._collection.Contains(component) == false)
            {
                GD.PrintErr("component not contains");
                return false;
            }
            component.Entity = null;
            component.Destroy();
			return this._collection.Remove(component);
		}

        public T GetComponent<T>() {
            // Type type = typeof(T);
            // foreach(dynamic comp in _collection)
            //     // if(comp.GetType() == type) return comp;
            //     if(comp.GetType() == type ||
            //        comp.GetType().BaseType == type) return comp;
            foreach(dynamic comp in _collection)
                if(comp is T) return comp;
            return default;
        }

        internal Component GetComponent(Type type) {
            foreach(var comp in _collection)
                // if(comp.GetType() == type) return comp; // child type only
                // if(comp.GetType() == type ||
                //    comp.GetType().BaseType == type) return comp; // child and parent type
                if(comp.GetType().IsAssignableTo(type)) return comp;
            return null;
        }

        // internal void DestroyComponent(Component component)
        // {
        //     int index = -1;
        //     for(var i=0;i<_collection.Count;++i)
        //         if(_collection[i] == component) {
        //             index = i;
        //             break;
        //         }
        //     if(index < 0)
        //         throw new Exception("error:");

        //     _collection.RemoveAt(index);
        //     component.Destroy();
        // }

        virtual internal void OnDestory() {
            foreach(var component in _collection)
                component.Destroy();
        }
        
        virtual internal void OnCreate() {
            foreach(var component in _collection)
                component.Create();
        }

        public bool IsValidComponents()
        {
            foreach(var c in _collection)
            {
                if(c.Entity != this) return false;
            }
            return true;
        }

    }

    public abstract class Component
    {
        public Entity Entity {get; internal set;}
        // public Component(Entity parent) {
        //     Entity = parent;
        // }
		public Component() {}

        virtual public void Create() {}
        virtual public void Destroy() {}
    }

	public class System
    {
		internal ECS _hub;
        internal Group _group;
        // public SystemHub Hub {get; private set;}
        // private Queue<HubMessage> _msgQ = new Queue<HubMessage>();

        public Type[] Filter { get; private set; }
        public System(params Type[] types) {
            Filter = new Type[types.Length];
            if(Filter.Length > 0)
                types.CopyTo(Filter,0);
            
            _group = new Group(this);
        }

        public bool Step(int step) {//}, bool systemDependence=true) {
            // MsgProc();
            
            // if(systemDependence && group.System != this) return false;

            var allComponents = _group.FilteredComponents();
            
#region only debug
            // foreach(var comps in allComponents) {
            //     if(checkType(comps) == false)
            //         throw new Exception();
            // }
#endregion

            Proc(step, allComponents.AsSpan());
            return true;
        }

        public virtual void Destroy() {}

        protected virtual void Proc(int step, Span<Component[]> allComponents) {}

        public int UpdateGroup(List<Entity> entities) {
            return this._group.Update(entities);
        }

        public bool UpdateGroup(Entity entity) {
            return this._group.Update(entity);
        }
    }

	public class Group
    {
        internal System _parent;

        public List<(Entity entity, Component[] components)> _group = new List<(Entity,Component[])>();

        public Group(System system) {
            _parent = system;
        }
        static private Component[] filter(Entity entity, Type[] types) {
            // if(types == null)
            //     throw new Exception("types is null");
            // if(entity == null)
            //     throw new Exception("entity is null");
            
            var _filter = new Component[types.Length];
            var valid_count = 0;

            for(int i=0;i<types.Length;++i) {
                var comp = entity.GetComponent(types[i]);
                if(comp != null) {
                    _filter[i] = comp;
                    ++valid_count;
                }
            }

            if(valid_count != types.Length) return null;

            return _filter;
        }

        public int Update(List<Entity> entities) {
            _group.Clear();
            foreach(var entity in entities) {
                if(entity.IsValidComponents() == false) {
                    GD.PrintErr("invalid components 3");
                    throw new Exception();
                }
                var comps = filter(entity,_parent.Filter);
                if(comps == null)
                    continue;
#region check
                int idx = -1;
                foreach(var c in comps) {
                    if(idx == -1)
                        idx = c.Entity.Id;
                    else if(idx != c.Entity.Id) {
                        GD.PrintErr($"entity not same:{idx}/{c.Entity.Id}({c})");
                        throw new Exception();
                    }
                }
#endregion
                _group.Add((entity, comps));
            }
            return _group.Count;
        }

        public bool Update(Entity entity) {
            if(entity.IsValidComponents() == false) {
                GD.PrintErr("invalid components");
                throw new Exception();
            }

            for(int i=0;i<_group.Count;++i)
            {
                if(_group[i].entity == entity) {
                    
                    var comps = filter(entity,_parent.Filter);
                    if(comps == null) {
                        // GD.PrintErr("개수 안맞음");
                        return false;
                    }
#region check
                int idx = -1;
                foreach(var c in comps) {
                    if(idx == -1)
                        idx = c.Entity.Id;
                    else if(idx != c.Entity.Id) {
                        GD.PrintErr($"entity not same:{idx}/{c.Entity.Id}({c})");
                        throw new Exception();
                    }
                }
#endregion
                    _group[i] = (entity, comps);
                    return true;
                }
            }
            // GD.PrintErr("못찾음. 없는 듯?");
            return false;
        }

        public Component[][] FilteredComponents() {
            var res = new Component[_group.Count][];
            for(int i=0;i<_group.Count;++i)
                res[i] = _group[i].components;
            return res;
        }
    }

	public class ECS
    {
        protected List<Entity> _entities = new List<Entity>();
        private List<System> _systems = new List<System>();

        // private Queue<HubMessage> _queue = new Queue<HubMessage>();
        private Dictionary<string, System> _named = new Dictionary<string, System>();
        
        public ECS(){}
        ~ECS() {
            Destroy();
        }

        public int CountEnt() { return _entities.Count; }
        public int CountSys() { return _systems.Count; }

        public List<System> GetAllSystem() {return _systems;}

        internal System AddSystem(System system, string name=null)
        {
            if(system == null)
                throw new ArgumentException("Parameter cannot be null", "original");
			system._hub = this;

            var group = new Group(system);
            group.Update(_entities);
            
            _systems.Add(system);

            if(name != null)
                _named.Add(name, system);
            // system.SetSystemHub(this);

            return system;
        }

        internal void RemoveEntAll()
        {
            foreach(var entity in _entities)
                entity.OnDestory();
            _entities.Clear();
        }

        internal void Destroy()
        {
            foreach(var system in _systems)
            {
                system.Destroy();
            }
        }

        internal List<object> FindEntAll<T>()
        {
            return _entities.FindAll(x=>x is T).ConvertAll(x=>(object)x);
        }

        internal Span<Entity> GetEntities()
        {
            return _entities.ToArray().AsSpan();
        }

        // public bool SendMessage(string name, HubMessage msg) {
        //     if(name == null)
        //         throw new ArgumentException("Parameter cannot be null", "original");
            
        //     System sys;
        //     if(_named.TryGetValue(name, out sys)== false)
        //         return false;
            
        //     sys.EnQueue(msg);
        //     return true;
        // }

        internal virtual bool AddEntity(Entity entity) {

            foreach(var e in _entities)
                if(e.IsValidComponents() == false)
                    GD.PrintErr("ci 0");

            if(_entities.Contains(entity))
                return false;

#region components check
            {
                if(entity.IsValidComponents() == false) {
                    GD.PrintErr("components invalid 1");
                    throw new Exception();
                }
            }
#endregion

            foreach(var e in _entities)
                if(e.IsValidComponents() == false)
                    GD.PrintErr("ci 1");

            _entities.Add(entity);
            entity.OnCreate();

#region components check
            {
                if(entity.IsValidComponents() == false) {
                    GD.PrintErr("components invalid 2");
                    throw new Exception();
                }
            }
#endregion


            foreach(var e in _entities)
                if(e.IsValidComponents() == false)
                    GD.PrintErr("ci 3");

            foreach(var system in _systems)
                system.UpdateGroup(_entities);

            return true;
        }

        internal bool RemoveEntity(Entity entity) {
            if(!_entities.Contains(entity))
                return false;
            
            entity.OnDestory();

            if(_entities.Remove(entity) == false)
                return false;
            
            foreach(var system in _systems)
                system.UpdateGroup(_entities);
            
            return true;
        }

        // internal bool UpdateEntity(Entity entity) {
        //     if(!_entities.Contains(entity))
        //         return false;
            
        //     foreach(var system in _systems)
        //         system.UpdateGroup(_entities);

        //     return true;
        // }

        internal System GetSystem(string name)
        {
            System sys;
            if(_named.TryGetValue(name, out sys) == false)
                throw new NullReferenceException();
            return sys;
        }

        internal System FindSystem(string name)
        {
            System sys;
            if(_named.TryGetValue(name, out sys) == false)
                return null;
            return sys;
        }

        internal void Step(int step)
        {
            for(var i=0;i<_systems.Count;++i) {
                _systems[i].Step(step);
            }

            foreach(var entity in this._entities)
                entity.ReleaseUpdated(this);
        }

        // internal void RemoveAll()
        // {
        //     foreach(var entity in _entities)
        //         entity.Destory();
        //     _entities.Clear();
        //     foreach(var group in _groups)
        //         group.Update(_entities);

        // }
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///

// using System.Collections.Generic;
// using System.Data;

// //https://matthall.codes/blog/ecs/

// namespace SE
// {
// 	public class Entity
// 	{
// 		public int ID { get; set; }

//     	public List<Component> components = new List<Component>();

// 		public void AddComponent(Component component)
// 		{
// 			components.Add(component);
// 			component.entity = this;
// 	    }

// 		public T GetComponent<T>() where T : Component
// 		{
// 			foreach (Component component in components)
// 			{
// 				if (component.GetType().Equals(typeof(T)))
// 				{
// 					return (T)component;
// 				}
// 			}
// 			return null;
// 		}
// 	}

// 	public class Component
// 	{
// 		public Entity entity;

//     	public virtual void Update(Value delta) { }
// 	}

// 	public class System<T> where T : Component
// 	{
// 		protected static List<T> components = new List<T>();

// 		public static void Register(T component)
// 		{
// 			components.Add(component);
// 		}
// 		public void Update(Value deltaTime)
// 		{
// 			foreach(T component in components)
// 			{
// 				component.Update(deltaTime);
// 			}
// 		}
// 	}
// }