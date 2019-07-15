from info import create_app, db, models
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand


# 数据库迁移拓展
app = create_app("development")
manager = Manager(app)
Migrate(app, db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()