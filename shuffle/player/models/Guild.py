
class Guild:
    def __init__(self, guild_id: int) -> None:
        self.id = guild_id

        self.prefix = '-'
    
    def __repr__(self) -> str:
        return f'Guild[id={self.id}]'
