"""
Example script showing how to configure and use email publishing for fantasy recaps.

This script demonstrates:
1. Setting up SMTP configuration
2. Adding league member emails
3. Enabling email recaps
4. Testing the email functionality
"""

import asyncio
import os
from datetime import datetime

from database.connection import AsyncSessionLocal
from models.league import League
from utilities.email_helper import (
    add_league_member_email,
    set_league_member_emails,
    enable_email_recaps,
    get_league_email_settings
)
from publishers.email_publisher import EmailPublisher
from services.recap_service import RecapService


async def setup_email_configuration():
    """
    Example of setting up email configuration.
    
    You'll need to set these environment variables or update your .env file:
    """
    print("=== Email Configuration Setup ===")
    print("Add these to your .env file or environment variables:")
    print()
    print("# Gmail example:")
    print("SMTP_SERVER=smtp.gmail.com")
    print("SMTP_PORT=587")
    print("SMTP_USERNAME=your-email@gmail.com")
    print("SMTP_PASSWORD=your-app-password")  # Use App Password for Gmail
    print("SMTP_FROM_EMAIL=your-email@gmail.com")
    print()
    print("# Outlook/Hotmail example:")
    print("SMTP_SERVER=smtp-mail.outlook.com")
    print("SMTP_PORT=587")
    print("SMTP_USERNAME=your-email@outlook.com")
    print("SMTP_PASSWORD=your-password")
    print("SMTP_FROM_EMAIL=your-email@outlook.com")
    print()


async def configure_league_emails(league_id: int):
    """
    Example of configuring email settings for a specific league.
    
    Args:
        league_id: The ID of the league to configure
    """
    async with AsyncSessionLocal() as db:
        print(f"=== Configuring League {league_id} ===")
        
        # Option 1: Add emails one by one
        emails_to_add = [
            "league.member1@gmail.com",
            "league.member2@yahoo.com",
            "league.member3@outlook.com"
        ]
        
        for email in emails_to_add:
            success = await add_league_member_email(db, league_id, email)
            if success:
                print(f"✓ Added: {email}")
            else:
                print(f"✗ Failed to add: {email}")
        
        # Option 2: Set all emails at once (replaces existing list)
        # all_emails = [
        #     "member1@gmail.com",
        #     "member2@yahoo.com",
        #     "member3@outlook.com",
        #     "member4@hotmail.com"
        # ]
        # await set_league_member_emails(db, league_id, all_emails)
        
        # Enable email recaps for the league
        await enable_email_recaps(db, league_id, True)
        print("✓ Email recaps enabled")
        
        # Check current settings
        settings = await get_league_email_settings(db, league_id)
        if settings:
            print(f"\nCurrent settings for {settings['league_name']}:")
            print(f"- Email recaps enabled: {settings['enable_email_recaps']}")
            print(f"- Number of recipients: {settings['email_count']}")
            print(f"- Email addresses: {', '.join(settings['member_emails'])}")


async def test_email_functionality(league_id: int):
    """
    Test the email functionality by sending a test email.
    
    Args:
        league_id: The ID of the league to test
    """
    print(f"=== Testing Email for League {league_id} ===")
    
    # Test basic email publisher
    publisher = EmailPublisher()
    
    test_emails = ["test@example.com"]  # Replace with actual test email
    test_subject = "🏈 Test Fantasy Football Recap"
    test_content = """
🏆 WEEKLY RECAP - Test League Week 1

📊 STANDINGS UPDATE
═══════════════════════════════
1. Team Alpha (3-0) - 145.6 pts
2. Team Beta (2-1) - 138.2 pts
3. Team Gamma (1-2) - 132.8 pts

💰 WAIVER WIRE ACTIVITY
═══════════════════════════════
• Team Alpha: Added RB Handcuff ($15 FAAB)
• Team Beta: Added WR Sleeper ($8 FAAB)

🔥 WEEKLY HIGHLIGHTS
═══════════════════════════════
• Highest scoring team: Team Alpha (145.6)
• Biggest blowout: Team Alpha vs Team Delta (145.6 - 89.2)
• Closest matchup: Team Beta vs Team Gamma (138.2 - 132.8)

Keep the trades coming and may your waiver claims be successful! 🏈

---
AI Commissioner Bot
    """.strip()
    
    try:
        success = await publisher.send_email(
            to_emails=test_emails,
            subject=test_subject,
            text_body=test_content
        )
        
        if success:
            print("✓ Test email sent successfully!")
        else:
            print("✗ Failed to send test email")
            
    except Exception as e:
        print(f"✗ Error testing email: {e}")


async def test_recap_service(league_id: int):
    """
    Test the full recap service with email publishing.
    
    Args:
        league_id: The ID of the league to test
    """
    print(f"=== Testing Recap Service for League {league_id} ===")
    
    service = RecapService()
    try:
        # Generate and publish a power rankings recap
        recap_text = await service.generate_power_rankings_recap(
            league_id=league_id,
            week=1,
            publish=True  # This will send to both GroupMe and Email if configured
        )
        
        print("✓ Power rankings recap generated and published")
        print(f"Recap length: {len(recap_text)} characters")
        
    except Exception as e:
        print(f"✗ Error testing recap service: {e}")
    finally:
        await service.close()


async def main():
    """Main example function."""
    # Replace with your actual league ID
    LEAGUE_ID = 1
    
    print("🏈 Fantasy Football Email Publisher Setup Example\n")
    
    # Show configuration setup
    await setup_email_configuration()
    
    # Configure league emails (uncomment to use)
    # await configure_league_emails(LEAGUE_ID)
    
    # Test basic email functionality (uncomment to use)
    # await test_email_functionality(LEAGUE_ID)
    
    # Test full recap service (uncomment to use)
    # await test_recap_service(LEAGUE_ID)
    
    print("\n🎉 Setup complete! Your league members will now receive recaps via email.")
    print("\nNext steps:")
    print("1. Set up your SMTP configuration in .env")
    print("2. Add league member emails using the helper functions")
    print("3. Enable email recaps for your leagues")
    print("4. Test with a sample email")
    print("5. Your scheduled recaps will now go to both GroupMe and Email!")


if __name__ == "__main__":
    asyncio.run(main())
