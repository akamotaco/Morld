namespace Morld;

/// <summary>
/// 데이터 프로바이더 인터페이스
/// 플러그인 시스템이 자체 데이터를 저장/로드할 수 있게 함
/// </summary>
public interface IDataProvider
{
	/// <summary>
	/// 데이터 프로바이더 고유 ID (파일명 결정에 사용)
	/// 예: "inventory" → inventory_data.json
	/// </summary>
	string DataId { get; }

	/// <summary>
	/// 데이터를 JSON 파일로 저장
	/// </summary>
	/// <param name="basePath">기본 경로 (예: "res://scripts/morld/json_data/")</param>
	void SaveData(string basePath);

	/// <summary>
	/// JSON 파일에서 데이터 로드
	/// </summary>
	/// <param name="basePath">기본 경로</param>
	/// <returns>로드 성공 여부</returns>
	bool LoadData(string basePath);

	/// <summary>
	/// 데이터 초기화 (파일이 없을 때 기본 상태로)
	/// </summary>
	void ClearData();
}
