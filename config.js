// 파이어베이스 웹 앱 설정. 파이어베이스 콘솔 > 프로젝트 설정 > 내 앱(웹)에서 받은 값을 넣습니다.
// 비어 있으면 가입 신청 단추가 "준비 중"으로 보입니다.
window.JACE_FIREBASE = {
  apiKey: "",
  authDomain: "jace-edulab.firebaseapp.com",
  databaseURL: "https://jace-edulab-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "jace-edulab",
  appId: ""
};
// 회원 관리(승인·명단 복사)를 할 수 있는 운영진 구글 계정. 데이터베이스 규칙의 이메일과 같아야 합니다.
window.JACE_ADMINS = ["jace.edulab@gmail.com"];
