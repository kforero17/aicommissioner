"""Email publisher for sending fantasy sports recaps via email."""
import asyncio
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime

import aiosmtplib

from config import settings


class EmailPublisher:
    """Publisher for sending emails to league members."""
    
    def __init__(
        self, 
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.smtp_server = smtp_server or settings.smtp_server
        self.smtp_port = smtp_port or settings.smtp_port
        self.username = username or settings.smtp_username
        self.password = password or settings.smtp_password
        self.from_email = settings.smtp_from_email or self.username
    
    async def _create_connection(self) -> aiosmtplib.SMTP:
        """Create and configure async SMTP connection."""
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            raise ValueError("SMTP configuration is incomplete")
        
        # Create async SMTP connection
        smtp = aiosmtplib.SMTP(
            hostname=self.smtp_server,
            port=self.smtp_port,
            use_tls=(self.smtp_port == 465),
            start_tls=(self.smtp_port == 587)
        )
        
        await smtp.connect()
        await smtp.login(self.username, self.password)
        return smtp
    
    async def send_email(
        self, 
        to_emails: List[str], 
        subject: str, 
        text_body: str,
        html_body: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email to multiple recipients.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            text_body: Plain text email body
            html_body: Optional HTML email body
            cc_emails: Optional CC recipients
            bcc_emails: Optional BCC recipients
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not to_emails or not subject or not text_body:
            print("Missing required email parameters")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add text part
            text_part = MIMEText(text_body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Prepare recipient list
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # Send email
            smtp = await self._create_connection()
            try:
                await smtp.send_message(msg)
                print(f"Successfully sent email to {len(all_recipients)} recipients")
                return True
            finally:
                await smtp.quit()
                
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    async def send_with_retry(
        self, 
        to_emails: List[str], 
        subject: str, 
        text_body: str,
        html_body: Optional[str] = None,
        max_retries: int = 3, 
        delay: float = 1.0
    ) -> bool:
        """
        Send email with retry logic.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            text_body: Plain text email body
            html_body: Optional HTML email body
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(max_retries + 1):
            success = await self.send_email(to_emails, subject, text_body, html_body)
            
            if success:
                return True
            
            if attempt < max_retries:
                print(f"Email attempt {attempt + 1} failed, retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
        
        print(f"Failed to send email after {max_retries + 1} attempts")
        return False
    
    def format_for_email(self, text: str, format_type: str = "text") -> str:
        """
        Format text for email display.
        
        Args:
            text: Original text
            format_type: "text" or "html"
            
        Returns:
            Formatted text appropriate for email
        """
        if format_type == "html":
            return self._convert_to_html(text)
        else:
            return text
    
    def _convert_to_html(self, text: str) -> str:
        """Convert plain text to basic HTML formatting."""
        # Replace newlines with <br> tags
        html = text.replace('\n', '<br>\n')
        
        # Add basic styling
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                {html}
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_recap_email(
        self,
        to_emails: List[str],
        league_name: str,
        week: int,
        recap_text: str,
        recap_type: str = "Weekly Recap"
    ) -> bool:
        """
        Send a fantasy football recap email.
        
        Args:
            to_emails: List of recipient email addresses
            league_name: Name of the fantasy league
            week: Week number
            recap_text: The recap content
            recap_type: Type of recap (e.g., "Weekly Recap", "Power Rankings", "Waiver Report")
            
        Returns:
            bool: True if successful, False otherwise
        """
        subject = f"🏈 {league_name} - Week {week} {recap_type}"
        
        # Create HTML version
        html_body = self._convert_to_html(recap_text)
        
        return await self.send_with_retry(
            to_emails=to_emails,
            subject=subject,
            text_body=recap_text,
            html_body=html_body
        )
    
    async def send_transaction_alert(
        self,
        to_emails: List[str],
        league_name: str,
        transaction_details: str
    ) -> bool:
        """
        Send a transaction alert email.
        
        Args:
            to_emails: List of recipient email addresses
            league_name: Name of the fantasy league
            transaction_details: Transaction details text
            
        Returns:
            bool: True if successful, False otherwise
        """
        subject = f"💰 {league_name} - New Transaction Activity"
        
        text_body = f"New transaction activity in {league_name}:\n\n{transaction_details}"
        html_body = self._convert_to_html(text_body)
        
        return await self.send_with_retry(
            to_emails=to_emails,
            subject=subject,
            text_body=text_body,
            html_body=html_body
        )
    
    async def send_league_update(
        self,
        to_emails: List[str],
        league_name: str,
        update_title: str,
        update_content: str
    ) -> bool:
        """
        Send a general league update email.
        
        Args:
            to_emails: List of recipient email addresses
            league_name: Name of the fantasy league
            update_title: Title of the update
            update_content: Update content
            
        Returns:
            bool: True if successful, False otherwise
        """
        subject = f"📢 {league_name} - {update_title}"
        html_body = self._convert_to_html(update_content)
        
        return await self.send_with_retry(
            to_emails=to_emails,
            subject=subject,
            text_body=update_content,
            html_body=html_body
        )


# Convenience function for simple usage
async def send_recap_email(
    to_emails: List[str], 
    league_name: str, 
    week: int, 
    recap_text: str,
    recap_type: str = "Weekly Recap"
) -> bool:
    """
    Simple function to send a recap email.
    
    Args:
        to_emails: List of recipient email addresses
        league_name: Name of the fantasy league
        week: Week number
        recap_text: The recap content
        recap_type: Type of recap
        
    Returns:
        bool: True if successful
    """
    publisher = EmailPublisher()
    return await publisher.send_recap_email(to_emails, league_name, week, recap_text, recap_type)


# Background task function
async def publish_recap_to_email(
    to_emails: List[str], 
    league_name: str, 
    week: int, 
    recap_text: str,
    recap_type: str = "Weekly Recap"
):
    """Background task to publish recap via email."""
    success = await send_recap_email(to_emails, league_name, week, recap_text, recap_type)
    if success:
        print(f"Successfully published {recap_type.lower()} to {len(to_emails)} email recipients")
    else:
        print(f"Failed to publish {recap_type.lower()} via email")
