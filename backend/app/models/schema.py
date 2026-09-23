from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime, Boolean,
    ForeignKey, Text, UniqueConstraint, Index
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

    profile_id = Column(String(64), primary_key=True)
    wmo_id = Column(String(16), ForeignKey("argo_floats.wmo_id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    qc_status = Column(String(32), default="QC_PASS_FLAG_1")
    raw_netcdf_source = Column(String(256), nullable=False)
    gdac_archive_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    float = relationship("ArgoFloat", back_populates="profiles")
    levels = relationship("ProfileLevel", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("wmo_id", "cycle_number", name="uq_float_cycle"),
        Index("idx_profiles_wmo_cycle", "wmo_id", "cycle_number"),
    )


class ProfileLevel(Base):
    __tablename__ = "profile_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String(64), ForeignKey("argo_profiles.profile_id"), nullable=False)
    depth_dbar = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)
    salinity = Column(Float, nullable=False)
    potential_density = Column(Float, nullable=False)

    profile = relationship("ArgoProfile", back_populates="levels")

    __table_args__ = (
        UniqueConstraint("profile_id", "depth_dbar", name="uq_profile_depth"),
        Index("idx_levels_profile", "profile_id"),
    )


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