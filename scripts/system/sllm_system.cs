// using Microsoft.ML.OnnxRuntimeGenAI;
// using Godot;
// using System.Threading.Tasks;
// using System;

// namespace SE
// {
//     public class sllmSystem : ECS.System
//     {
//         /// <summary>
//         /// slm (small language model) 테스트용 시스템.
//         /// onnxruntime.genai를 활용하여 테스트 중
//         /// </summary>
//         private Model _model;
//         private Tokenizer _tokenizer;
//         private GeneratorParams _generatorParams;
//         private Generator _generator;
//         private int _ptr;

//         public sllmSystem() : base()
//         {
//             GD.Print("[sllm system]");
                        
//             var modelPath = "res://resources/assets/model/sllm_i4_cpu";
//             modelPath = ProjectSettings.GlobalizePath(modelPath);

//             this._model = new Model(modelPath);
//             this._tokenizer = new Tokenizer(this._model);
//             this._generatorParams = new GeneratorParams(this._model);
//             this._generatorParams.SetSearchOption("max_length", 2048);


//             this.Call("나 오늘 너무 힘들었어...");
//             string res = "";
//             string partial;
//             GD.Print("[llm:response start]");
//             while(this.Generate(out partial)) {
//                 res += partial;
//             }
//             GD.Print(res);
//             GD.Print("[llm:response end]");
//         }

//         public void Call(string prompt)
//         {
//                 var prompt_template = $"system:You are a dialogue AI assistant\n질문:{prompt}\n대답:";

//                 var tokens = this._tokenizer.Encode(prompt_template);

//                 this._generatorParams.SetInputSequences(tokens);

//                 this._generator = new Generator(this._model, this._generatorParams);

//                 this._ptr = 0;
//                 this._ptr = tokens[0].Length; // skip prompt length
//         }

//         public bool Generate(out string response)
//         {
//             if(this._generator == null || this._generator.IsDone()) {
//                 response = "";
//                 return false;
//             }

//             this._generator.ComputeLogits();
//             this._generator.GenerateNextToken();
//             var outputTokens = this._generator.GetSequence(0);

//             // #if __OUT_DEFAULT__
//             // #region defualt stdout
//             //         var newToken = outputTokens.Slice(outputTokens.Length - 1, 1);
//             //         var output = tokenizer.Decode(newToken);
//             //         Console.Write(output);
//             // #endregion
//             // #else
//             #region print for cjk
//             var unReadToken = outputTokens.Slice(this._ptr);
//             var read = 0;
//             for(var i=0;i<unReadToken.Length;++i) {
//                 var t = this._tokenizer.Decode(unReadToken.Slice(i,1));
//                 var code = (int)t.ToCharArray()[^1];
//                 if(code != 0xFFFD) {// 65533
//                     read = i+1;
//                 }
//             }

//             if(read > 0) {
//                 this._ptr += read;
//                 var output = this._tokenizer.Decode(unReadToken.Slice(0, read));
//                 // Console.Write(output);
//                 // res += output;
//                 response = output;
//             }
//             else {
//                 response = "";
//             }
//             #endregion
//             // #endif
//                 // }
//                 // Console.WriteLine();
//             // GD.Print("[sllm:res]"+res);

//             // #region print at once
//             // #if __OUT_AT_ONCE__
//             //     {
//             //         Console.WriteLine("[== once ==]");
//             //         generator.ComputeLogits();
//             //         generator.GenerateNextToken();
//             //         var outputTokens = generator.GetSequence(0);
//             //         var output = tokenizer.Decode(outputTokens);
//             //         Console.Write(output);
//             //     }
//             // #endif
//             // #endregion

//             return true;
//         }
//     }
// }