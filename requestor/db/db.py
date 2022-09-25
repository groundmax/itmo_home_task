class DBService(BaseModel):
    pool: Pool

    class Config:
        arbitrary_types_allowed = True

    async def setup(self) -> None:
        await self.pool
        app_logger.info("Db service initialized")

    async def cleanup(self) -> None:
        await self.pool.close()
        app_logger.info("Db service shutdown")

    async def ping(self) -> bool:
        return await self.pool.fetchval("SELECT TRUE")

    async def add_new_report(self, user_id: UUID, filename: str) -> Report:
        query = """"""

    async def add_new_team(TeamInfo):
        pass

    async def update_team_info(TeamInfo):
        pass

    async def delete_team(team_id):
        pass

    async def add_obstrel(ObstrelInfo):
        pass

    async def set_obstrel_status(obstrel_id, status):
        pass

    async def add_model_metrics(obstrel_id, metrics):
        pass