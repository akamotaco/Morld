using ECS;
using Godot;
using System;

namespace SE
{
    public class logSystem : ECS.System
    {
        /// <summary>
        /// 로그 출력 시스템. 일단은 eneity를 개수하기 위해 임시로 구현
        /// 향후 텍스트 로그 출력 시스템으로 개조할 예정 있음
        /// </summary>
        private TextEdit textEdit;
        private int updateTerm = 0;
        private const int term = 1000; // 1 bsec

        public logSystem(TextEdit textEdit)
        {
            this.textEdit = textEdit;
        }

        protected override void Proc(int step, Span<Component[]> allComponents)
        {
            base.Proc(step, allComponents);

            updateTerm += step;
            if(updateTerm >= term) {
                updateTerm = 0;
                this.textEdit.Text = "entities:"+_hub.CountEnt();;
            }
        }
    }
}