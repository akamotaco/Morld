# assets/locations/corridor_2f.py - 복도 2층 (Location 8)
#
# 그림 액자에서 숫자 힌트 "4", "9", 서재 문(비밀번호 2847)

from assets.base import Location


class Corridor2F(Location):
    unique_id = "corridor_2f"
    name = "복도 2층"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "2층 복도다. 벽에 걸린 그림 액자가 비스듬히 기울어져 있다. 복도 끝에 묵직한 참나무 문이 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 오브젝트 배치
        from assets.objects.corridor import PictureFrame, StudyDoor

        self.add_object(PictureFrame())
        self.add_object(StudyDoor())
