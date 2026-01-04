# assets/objects/__init__.py - 오브젝트 Asset 모듈
#
# 데코레이터(@register_object)로 import 시 자동 등록됩니다.

# 오브젝트 모듈 import (데코레이터 실행으로 자동 등록)
from . import grounds   # 바닥 오브젝트 (Location에서 참조)
from . import furniture  # 가구류
from . import outdoor    # 야외 오브젝트
