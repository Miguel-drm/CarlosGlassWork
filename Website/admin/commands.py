import click
from flask.cli import with_appcontext
from firebase_admin import auth


def init_admin_commands(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    def create_admin(email):
        """Make a specific user an admin by their email"""
        try:
            user = auth.get_user_by_email(email)
            # Only set admin claim for the specified user
            auth.set_custom_user_claims(user.uid, {"admin": True})
            click.echo(f"Successfully made {email} an admin")
        except Exception as e:
            click.echo(f"Error: {str(e)}")

    @app.cli.command("list-users")
    def list_users():
        """List all users in Firebase"""
        try:
            users = auth.list_users()
            click.echo("\nFirebase Users:")
            click.echo("--------------")
            for user in users.users:
                is_admin = (
                    user.custom_claims.get("admin", False)
                    if user.custom_claims
                    else False
                )
                click.echo(f"Email: {user.email} {'(Admin)' if is_admin else ''}")
            click.echo("--------------")
        except Exception as e:
            click.echo(f"Error: {str(e)}")

    @app.cli.command("check-user")
    @click.argument("email")
    def check_user_status(email):
        """Check if a user is admin or regular user by email"""
        try:
            user = auth.get_user_by_email(email)
            click.echo("\nUser Details:")
            click.echo("--------------")
            click.echo(f"Email: {user.email}")
            click.echo(f"Display Name: {user.display_name or 'Not Set'}")

            # Check admin status
            is_admin = (
                user.custom_claims.get("admin", False) if user.custom_claims else False
            )
            role = "Admin" if is_admin else "Regular User"
            click.echo(f"Role: {role}")
            click.echo(f"User ID: {user.uid}")
            click.echo("--------------")
        except auth.UserNotFoundError:
            click.echo(f"Error: User with email {email} not found")
        except Exception as e:
            click.echo(f"Error: {str(e)}")

