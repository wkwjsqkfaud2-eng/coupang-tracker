"""쿠팡 파트너스 Open API 클라이언트 (추가 설치 필요 없음)"""
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

DOMAIN = "https://api-gateway.coupang.com"
BASE = "/v2/providers/affiliate_open_api/apis/openapi/v1"


class CoupangAPI:
    def __init__(self, access_key, secret_key, sub_id=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.sub_id = sub_id
        self._calls = []  # 분당 100회 제한 지키기용

    def _auth(self, method, path, query):
        signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
        message = signed_date + method + path + query
        signature = hmac.new(self.secret_key.encode(), message.encode(),
                             hashlib.sha256).hexdigest()
        return (f"CEA algorithm=HmacSHA256, access-key={self.access_key}, "
                f"signed-date={signed_date}, signature={signature}")

    def _throttle(self):
        now = time.time()
        self._calls = [t for t in self._calls if now - t < 60]
        if len(self._calls) >= 90:  # 여유 있게 90회
            time.sleep(60 - (now - self._calls[0]) + 1)
        self._calls.append(time.time())

    def _get(self, path, params):
        if self.sub_id:
            params["subId"] = self.sub_id
        query = urllib.parse.urlencode(params)
        full_path = BASE + path
        self._throttle()
        req = urllib.request.Request(
            f"{DOMAIN}{full_path}?{query}",
            headers={"Authorization": self._auth("GET", full_path, query),
                     "Content-Type": "application/json;charset=UTF-8"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"API 오류 {e.code}: {e.read()[:300]!r}") from None
        if str(body.get("rCode", "0")) != "0":
            raise RuntimeError(f"API 응답 오류: {body.get('rMessage')}")
        return body.get("data")

    # 상품 검색 (1시간 10회 제한!)
    def search(self, keyword, limit=10):
        data = self._get("/products/search", {"keyword": keyword, "limit": limit})
        return (data or {}).get("productData", [])

    # 카테고리 베스트
    def best(self, category_id, limit=50):
        return self._get(f"/products/bestcategories/{category_id}",
                         {"limit": limit}) or []

    # 골드박스 (매일 오전 7:30 갱신되는 특가)
    def goldbox(self):
        return self._get("/products/goldbox", {}) or []
