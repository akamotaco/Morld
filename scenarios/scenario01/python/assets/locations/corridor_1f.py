# assets/locations/corridor_1f.py - 복도 1층 (Location 4)
#
# 괘종시계에서 "1842년" 힌트, 우산꽂이는 플레이버 텍스트

from assets.base import Location


class Corridor1F(Location):
    unique_id = "corridor_1f"
    name = "복도 1층"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "길게 뻗은 복도다. 벽에 걸린 초상화들이 지나가는 이를 응시하는 듯하다. 괘종시계가 묵묵히 서 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.corridor import GrandfatherClock, UmbrellaStand

        self.add_object(GrandfatherClock(), 115)
        self.add_object(UmbrellaStand(), 116)
