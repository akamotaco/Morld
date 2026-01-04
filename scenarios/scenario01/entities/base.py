# entities/base.py - 모든 엔티티의 기본 클래스

class BaseEntity:
    """모든 엔티티의 기본 클래스"""

    ID: int = 0
    NAME: str = ""

    def register(self):
        """morld에 엔티티 등록 - 서브클래스에서 구현"""
        raise NotImplementedError(f"{type(self).__name__}.register() not implemented")

    def unregister(self):
        """morld에서 엔티티 등록 해제 - 서브클래스에서 구현"""
        pass
