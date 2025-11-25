import json
import random
from sqlalchemy import select, insert, update
from database.engine import async_session
from database.models import SampleReport


class SampleReportsService:
    
    @staticmethod
    async def get_random_sample_report(video_type: str = 'regular'):
        async with async_session() as session:
            result = await session.execute(
                select(SampleReport)
                .where(SampleReport.is_active == True)
                .where(SampleReport.video_type == video_type)  # 🆕 YANGI
            )
            reports = result.scalars().all()
            
            if not reports:
                return None
            
            selected_report = random.choice(reports)
            
            return {
                'id': selected_report.id,
                'report_name': selected_report.report_name,
                'video_url': selected_report.video_url,
                'video_type': selected_report.video_type,  # 🆕 YANGI
                'analysis_data': json.loads(selected_report.analysis_data),
                'is_active': selected_report.is_active,
                'created_at': selected_report.created_at
            }
    
    @staticmethod
    async def get_all_sample_reports(active_only: bool = True):
        async with async_session() as session:
            query = select(SampleReport)
            
            if active_only:
                query = query.where(SampleReport.is_active == True)
            
            result = await session.execute(query.order_by(SampleReport.created_at.desc()))
            reports = result.scalars().all()
            
            return [
                {
                    'id': report.id,
                    'report_name': report.report_name,
                    'video_url': report.video_url,
                    'analysis_data': json.loads(report.analysis_data),
                    'is_active': report.is_active,
                    'created_at': report.created_at
                }
                for report in reports
            ]
    
    @staticmethod
    async def get_sample_report_by_id(report_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(SampleReport).where(SampleReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            
            if not report:
                return None
            
            return {
                'id': report.id,
                'report_name': report.report_name,
                'video_url': report.video_url,
                'analysis_data': json.loads(report.analysis_data),
                'is_active': report.is_active,
                'created_at': report.created_at
            }
    
    @staticmethod
    async def add_sample_report(report_name: str, video_url: str, analysis_data: dict, video_type: str = 'regular'):
        async with async_session() as session:
            stmt = insert(SampleReport).values(
                report_name=report_name,
                video_url=video_url,
                video_type=video_type,  # 🆕 YANGI
                analysis_data=json.dumps(analysis_data, ensure_ascii=False),
                is_active=True
            )
            result = await session.execute(stmt)
            await session.commit()
            
            return result.inserted_primary_key[0]
    
    @staticmethod
    async def activate_sample_report(report_id: int):
        async with async_session() as session:
            stmt = update(SampleReport).where(
                SampleReport.id == report_id
            ).values(is_active=True)
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def deactivate_sample_report(report_id: int):
        async with async_session() as session:
            stmt = update(SampleReport).where(
                SampleReport.id == report_id
            ).values(is_active=False)
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def update_sample_report(report_id: int, **kwargs):
        async with async_session() as session:
            if 'analysis_data' in kwargs and isinstance(kwargs['analysis_data'], dict):
                kwargs['analysis_data'] = json.dumps(kwargs['analysis_data'], ensure_ascii=False)
            
            stmt = update(SampleReport).where(
                SampleReport.id == report_id
            ).values(**kwargs)
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    @staticmethod
    async def get_active_reports_count():
        async with async_session() as session:
            from sqlalchemy import func
            
            result = await session.execute(
                select(func.count(SampleReport.id)).where(SampleReport.is_active == True)
            )
            return result.scalar() or 0