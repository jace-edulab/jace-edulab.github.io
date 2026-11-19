// 파이어베이스 웹 앱 설정. 파이어베이스 콘솔 > 프로젝트 설정 > 내 앱(웹)에서 받은 값을 넣습니다.
// 비어 있으면 가입 신청 단추가 "준비 중"으로 보입니다.
window.JACE_FIREBASE = {
  apiKey: "AIzaSyD_t8_g2A21ELTB91s6X0xwCd_3CCZ3Sms",
  authDomain: "jace-edulab.firebaseapp.com",
  databaseURL: "https://jace-edulab-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "jace-edulab",
  appId: "1:26042094593:web:82ffff662db66e5e805c00"
};
// 대표 계정: 가입 신청 없이 운영진으로 쓰고, 회원 명단에서는 빠집니다.
window.JACE_ADMINS = ["jace.edulab@gmail.com"];
// 회장 계정: 회원으로 가입하되(명단에 "회장"으로 들어감) 회원 관리 권한도 가집니다.
// 두 목록의 이메일은 데이터베이스 규칙의 이메일과 같아야 합니다.
window.JACE_MANAGERS = ["mistetbaram@gmail.com"];
