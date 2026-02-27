"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

이 파일은 Alembic이 자동 생성한 마이그레이션 스크립트입니다.
'alembic revision --autogenerate -m "설명"' 명령으로 생성됩니다.

적용:   alembic upgrade ${up_revision}
롤백:   alembic downgrade ${down_revision | comma,n}
"""
from typing import Sequence, Union

# ─── Alembic 마이그레이션 도구 ───
from alembic import op  # DDL 명령 (create_table, add_column, drop_table 등)
import sqlalchemy as sa  # 컬럼 타입 정의 (sa.String, sa.Integer 등)
${imports if imports else ""}

# ─── 마이그레이션 식별자 ───
# revision: 이 마이그레이션의 고유 ID (12자리 hex)
# down_revision: 이전 마이그레이션 ID (None이면 첫 번째 마이그레이션)
# branch_labels: 브랜치 레이블 (주로 None)
# depends_on: 의존하는 마이그레이션 ID (주로 None)
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """
    업그레이드 함수: 이 마이그레이션을 DB에 적용합니다.
    alembic upgrade head 명령 시 실행됩니다.

    일반적인 작업 예시:
      op.create_table(...)        # 테이블 생성
      op.add_column(...)          # 컬럼 추가
      op.alter_column(...)        # 컬럼 변경
      op.create_index(...)        # 인덱스 생성
      op.create_unique_constraint(...)  # UNIQUE 제약 추가
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    다운그레이드 함수: 이 마이그레이션을 롤백합니다.
    alembic downgrade -1 명령 시 실행됩니다.

    upgrade()의 역순으로 작업을 수행해야 합니다.
    예: create_table → drop_table, add_column → drop_column
    """
    ${downgrades if downgrades else "pass"}
