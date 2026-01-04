# assets/__init__.py - Asset Registry (scenario02)

import morld


class AssetRegistry:
    """
    Asset 관리 레지스트리

    - unique_id (str): Asset 탐색용 키
    - instance_id (int): 시스템 관리 고유 ID
    """

    def __init__(self):
        # Asset 저장소: unique_id → asset_data
        self._items = {}
        self._objects = {}
        self._characters = {}

        # Instance 매핑: unique_id → instance_id
        self._instance_map = {}

        # 역방향 매핑: instance_id → unique_id
        self._reverse_map = {}

    # ========================================
    # Asset 등록 (정의 시점)
    # ========================================

    def register_item(self, asset_data):
        """아이템 Asset 등록"""
        uid = asset_data["unique_id"]
        self._items[uid] = asset_data

    def register_object(self, asset_data):
        """오브젝트 Asset 등록"""
        uid = asset_data["unique_id"]
        self._objects[uid] = asset_data

    def register_character(self, asset_data):
        """캐릭터 Asset 등록"""
        uid = asset_data["unique_id"]
        self._characters[uid] = asset_data

    # ========================================
    # Asset 조회
    # ========================================

    def get_item(self, unique_id):
        """아이템 Asset 조회 (없으면 에러)"""
        if unique_id not in self._items:
            raise KeyError(f"[AssetRegistry] Item not found: {unique_id}")
        return self._items[unique_id]

    def get_object(self, unique_id):
        """오브젝트 Asset 조회 (없으면 에러)"""
        if unique_id not in self._objects:
            raise KeyError(f"[AssetRegistry] Object not found: {unique_id}")
        return self._objects[unique_id]

    def get_character(self, unique_id):
        """캐릭터 Asset 조회 (없으면 에러)"""
        if unique_id not in self._characters:
            raise KeyError(f"[AssetRegistry] Character not found: {unique_id}")
        return self._characters[unique_id]

    def get_all_characters(self):
        """모든 캐릭터 Asset 반환"""
        return self._characters

    # ========================================
    # Instance 생성 및 매핑
    # ========================================

    def instantiate_item(self, unique_id, instance_id, modify=None):
        """아이템 Asset을 Instance로 생성"""
        asset = self.get_item(unique_id).copy()

        if modify:
            self._apply_modify(asset, modify)

        self._instance_map[unique_id] = instance_id
        self._reverse_map[instance_id] = unique_id

        morld.add_item(
            instance_id,
            asset["name"],
            asset.get("passiveTags", {}),
            asset.get("equipTags", {}),
            asset.get("value", 0),
            asset.get("actions", [])
        )

        return asset

    def instantiate_object(self, unique_id, instance_id, region_id, location_id, modify=None):
        """오브젝트 Asset을 Instance로 생성"""
        asset = self.get_object(unique_id).copy()

        if modify:
            self._apply_modify(asset, modify)

        self._instance_map[unique_id] = instance_id
        self._reverse_map[instance_id] = unique_id

        morld.add_unit(
            instance_id,
            asset["name"],
            region_id,
            location_id,
            "object",
            asset.get("actions", []),
            asset.get("appearance", {}),
            []  # mood
        )

        return asset

    def instantiate_character(self, unique_id, instance_id, region_id, location_id, modify=None):
        """캐릭터 Asset을 Instance로 생성 (스케줄, 태그 포함)"""
        asset = self.get_character(unique_id).copy()

        if modify:
            self._apply_modify(asset, modify)

        self._instance_map[unique_id] = instance_id
        self._reverse_map[instance_id] = unique_id

        # 기본 유닛 생성
        morld.add_unit(
            instance_id,
            asset["name"],
            region_id,
            location_id,
            asset.get("type", "male"),
            asset.get("actions", []),
            asset.get("appearance", {}),
            asset.get("mood", [])
        )

        # 태그 설정
        tags = asset.get("tags")
        if tags:
            morld.set_unit_tags(instance_id, tags)

        # 스케줄 스택 설정
        schedule_stack = asset.get("scheduleStack", [])
        for layer in schedule_stack:
            morld.push_schedule(
                instance_id,
                layer.get("name", ""),
                layer.get("endConditionType"),
                layer.get("endConditionParam"),
                layer.get("schedule")
            )

        return asset

    # ========================================
    # ID 조회
    # ========================================

    def get_instance_id(self, unique_id):
        """unique_id → instance_id (없으면 None)"""
        return self._instance_map.get(unique_id)

    def get_unique_id(self, instance_id):
        """instance_id → unique_id (없으면 None)"""
        return self._reverse_map.get(instance_id)

    def require_instance_id(self, unique_id):
        """unique_id → instance_id (없으면 에러)"""
        iid = self._instance_map.get(unique_id)
        if iid is None:
            raise KeyError(f"[AssetRegistry] No instance for: {unique_id}")
        return iid

    # ========================================
    # 내부 헬퍼
    # ========================================

    def _apply_modify(self, asset, modify):
        """modify dict를 asset에 적용 (shallow merge)"""
        for key, value in modify.items():
            if isinstance(value, dict) and isinstance(asset.get(key), dict):
                asset[key] = {**asset.get(key, {}), **value}
            else:
                asset[key] = value


# 전역 레지스트리 인스턴스
registry = AssetRegistry()


# ========================================
# Asset 로드 함수
# ========================================

def load_all_assets():
    """모든 Asset 로드 (정의만, 인스턴스화 X)"""
    from assets import items as item_assets
    from assets import objects as object_assets
    from assets import characters as character_assets

    item_assets.register_all()
    object_assets.register_all()
    character_assets.register_all()

    print("[assets] All assets loaded")
