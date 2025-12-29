
using System;
using Godot;
using ECS;
using System.Collections.Generic;

namespace SE
{
	// public abstract class Transaction
	// {
	// 	public enum Command
	// 	{
	// 		ADD_ENTITY,
	// 		DELETE_ENTITY,
	// 		UNKNOWN,
	// 	}

	// 	public Command Cmd { get; private set; }

	// 	public Transaction(Command cmd)
	// 	{
	// 		this.Cmd = cmd;
	// 	}
	// }

	public class World : ECS.ECS
	{
        public Node Root {get; private set;}

		// private Queue<Transaction> _q = new Queue<Transaction>();
		
        public World(Node root)
		{
			this.Root = root;
		}

        // internal override bool AddEntity(Entity entity)
        // {
		// 	if(entity.GetComponent<GodotAsset>() != null) {
		// 		this.Root.AddChild(entity.GetComponent<GodotAsset>().Node);
		// 	}
        //     return base.AddEntity(entity);
        // }

        public void Update(int deltaMs)
		{
			this.Step(deltaMs);

			// this.ProcessTransaction();
		}

        // private void ProcessTransaction()
        // {
        //     while(this._q.Count > 0)
		// 	{
		// 		var t  = this._q.Dequeue();
				
		// 		switch(t.Cmd)
		// 		{
		// 			default:
		// 				throw new Exception("unknown transaction:"+t);
		// 			case Transaction.Command.ADD_ENTITY:
		// 				TransactionAddEntity(t);
		// 				break;
		// 			case Transaction.Command.DELETE_ENTITY:
		// 				TransactionDeleteEntity(t);
		// 				break;
		// 		}
		// 	}
        // }

        // private void TransactionAddEntity(Transaction t)
        // {
        //     throw new NotImplementedException();
        // }

        // public void RegisterTransaction(Queue<Transaction> q)
		// {
		// 	ProcessTransaction();
		// 	this._q = q;
		// }

        // private void TransactionDeleteEntity(Transaction t)
        // {
        //     throw new NotImplementedException();
        // }
    }
}