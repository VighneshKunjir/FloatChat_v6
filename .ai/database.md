# FloatChat: Database Architecture & Schema

## 1. Relational Database Design
FloatChat uses an enterprise relational database structure (fully compatible with **SQLite** for instant zero-dependency local development, and **PostgreSQL 16** for containerized or production deployments).

---

## 2. Entity-Relationship (ER) Diagram

```
+-------------------+       1:N        +-----------------------+
|   argo_floats     |-----------------<|     argo_profiles     |
+-------------------+                  +-----------------------+
| PK  wmo_id        |                  | PK  profile_id        |
|     platform_name |                  | FK  wmo_id            |
|     base_lat      |                  |     cycle_number      |
|     base_lon      |                  |     date              |
|     institution   |                  |     latitude          |
|     status        |                  |     longitude         |
+-------------------+                  |     qc_status         |
                                       |     raw_netcdf_source |
                                       |     gdac_archive_path |
                                       +-----------------------+
                                                   |
                                                   | 1:N
                                                   v
                                       +-----------------------+
                                       |   profile_levels      |
                                       +-----------------------+
                                       | PK  id                |
                                       | FK  profile_id        |
                                       |     depth_dbar        |
                                       |     temperature       |
                                       |     salinity          |
                                       |     potential_density |
                                       +-----------------------+

+----------------------------+
|      forecast_logs         |
+----------------------------+
| PK  forecast_id            |
|     target_wmo_id          |
|     target_cycle           |
|     predicted_cycle        |
|     model_version          |
|     created_at             |
|     surface_temp_forecast  |
|     mld_dbar               |
|     is_stable              |
|     full_result_json       |
+----------------------------+
```

---

## 3. SQL Data Definition Language (DDL)

```sql
-- 1. Argo Floats Metadata
CREATE TABLE argo_floats (
    wmo_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    base_lat DOUBLE PRECISION NOT NULL,
    base_lon DOUBLE PRECISION NOT NULL,
    institution VARCHAR(64) DEFAULT 'INCOIS / Argo GDAC',
    status VARCHAR(32) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Argo Historical Profiles (Cycle Level)
CREATE TABLE argo_profiles (
    profile_id VARCHAR(64) PRIMARY KEY, -- e.g. '3902114_92'
    wmo_id VARCHAR(16) NOT NULL REFERENCES argo_floats(wmo_id) ON DELETE CASCADE,
    cycle_number INTEGER NOT NULL,
    date DATE NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    qc_status VARCHAR(32) DEFAULT 'QC_PASSED',
    raw_netcdf_source VARCHAR(256) NOT NULL,
    gdac_archive_path VARCHAR(512) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_float_cycle UNIQUE (wmo_id, cycle_number)
);

CREATE INDEX idx_profiles_wmo_cycle ON argo_profiles(wmo_id, cycle_number);

-- 3. Discrete Depth Measurements (16 Standard Levels per Profile)
CREATE TABLE profile_levels (
    id SERIAL PRIMARY KEY,
    profile_id VARCHAR(64) NOT NULL REFERENCES argo_profiles(profile_id) ON DELETE CASCADE,
    depth_dbar INTEGER NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    salinity DOUBLE PRECISION NOT NULL,
    potential_density DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_profile_depth UNIQUE (profile_id, depth_dbar)
);

CREATE INDEX idx_levels_profile ON profile_levels(profile_id);

-- 4. Forecast Execution & Audit Logs
CREATE TABLE forecast_logs (
    forecast_id VARCHAR(128) PRIMARY KEY,
    target_wmo_id VARCHAR(16) NOT NULL REFERENCES argo_floats(wmo_id),
    target_cycle INTEGER NOT NULL,
    predicted_cycle INTEGER NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    surface_temp_forecast DOUBLE PRECISION NOT NULL,
    mixed_layer_depth_m DOUBLE PRECISION NOT NULL,
    is_gravitationally_stable BOOLEAN NOT NULL,
    full_result_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. SQLAlchemy 2.0 ORM Models (Python)

```python
# backend/app/models/schema.py
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime, Boolean,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ArgoFloat(Base):
    __tablename__ = "argo_floats"

    wmo_id = Column(String(16), primary_key=True)
    name = Column(String(128), nullable=False)
    base_lat = Column(Float, nullable=False)
    base_lon = Column(Float, nullable=False)
    institution = Column(String(64), default="INCOIS / Argo GDAC")
    status = Column(String(32), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("ArgoProfile", back_populates="float", cascade="all, delete-orphan")


class ArgoProfile(Base):
    __tablename__ = "argo_profiles"

    profile_id = Column(String(64), primary_key=True) # e.g. '3902114_92'
    wmo_id = Column(String(16), ForeignKey("argo_floats.wmo_id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    qc_status = Column(String(32), default="QC_PASSED")
    raw_netcdf_source = Column(String(256), nullable=False)
    gdac_archive_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    float = relationship("ArgoFloat", back_populates="profiles")
    levels = relationship("ProfileLevel", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("wmo_id", "cycle_number", name="uq_float_cycle"),)


class ProfileLevel(Base):
    __tablename__ = "profile_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String(64), ForeignKey("argo_profiles.profile_id"), nullable=False)
    depth_dbar = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)
    salinity = Column(Float, nullable=False)
    potential_density = Column(Float, nullable=False)

    profile = relationship("ArgoProfile", back_populates="levels")

    __table_args__ = (UniqueConstraint("profile_id", "depth_dbar", name="uq_profile_depth"),)


class ForecastLog(Base):
    __tablename__ = "forecast_logs"

    forecast_id = Column(String(128), primary_key=True)
    target_wmo_id = Column(String(16), nullable=False)
    target_cycle = Column(Integer, nullable=False)
    predicted_cycle = Column(Integer, nullable=False)
    model_version = Column(String(64), nullable=False)
    surface_temp_forecast = Column(Float, nullable=False)
    mixed_layer_depth_m = Column(Float, nullable=False)
    is_gravitationally_stable = Column(Boolean, nullable=False)
    full_result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 5. Seed Data Strategy
The backend seed script (`backend/scripts/seed_db.py`) ingests data from the five Arabian Sea reference floats (`3902114`, `2902084`, `2902266`, `2902123`, `2902099`), populating all 440+ historical cycles and 7,000+ vertical levels.

Commands to seed:
```bash
# For local SQLite:
python backend/scripts/seed_db.py --db-url "sqlite:///./backend/data/floatchat.db"

# For local PostgreSQL:
python backend/scripts/seed_db.py --db-url "postgresql://postgres:postgres@localhost:5432/floatchat"
```
