"""Windows용 codebook 빌드 runner. 원본 codebook_builder.py의 __main__을 경로 수정해서 실행."""
import sys
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from codebook_builder import build_codebook, save_codebook
from state_v2 import load_character

root = HERE
out_dir = root / "codebooks"
out_dir.mkdir(exist_ok=True)

for yaml_path in sorted((root / "examples").glob("*.yaml")):
    npc, samples = load_character(str(yaml_path))
    cb = build_codebook(npc, samples)
    print(f"\n=== {npc.name} ({npc.archetype}) ===")
    print(f"  samples:  {len(samples)}")
    print(f"  tokens:   {len(cb.tokens)}")
    by_class = Counter(t.tclass for t in cb.tokens)
    print(f"  classes:  {dict(by_class)}")
    save_codebook(cb, str(out_dir / f"{npc.name}.json"))
    print(f"  -> saved {out_dir / npc.name}.json")
