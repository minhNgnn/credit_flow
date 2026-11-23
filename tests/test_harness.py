"""Harness smoke test — chứng minh test chạy được trước khi viết endpoint.

Không dùng GET /health: endpoint đó kiểm cả Redis, mà redis trong
docker-compose.yml không bind ra host (chỉ trong network `internal`), nên
từ host nó luôn 503. Các endpoint intake không chạm Redis — chúng chỉ cần
Postgres + MinIO — nên harness kiểm đúng hai thứ đó thay vì nới
docker-compose chỉ để chiều một test.
"""
from shared.db import ping as db_ping
from shared.storage import ensure_bucket


def test_postgres_reachable():
    assert db_ping() is True


def test_minio_reachable():
    ensure_bucket()


def test_app_boots_with_intake_router(client):
    """App import và khởi động được sau khi mount intake.router.

    GET /cases là endpoint có sẵn của cases.router — dùng nó vì
    intake.router ở Task 1 còn rỗng, chưa có route nào để gọi. Test này
    chỉ chứng minh việc thêm include_router không làm app sập lúc import
    (trùng prefix, lỗi cú pháp, import vòng).
    """
    response = client.get("/cases")
    assert response.status_code == 200
