"""GroupMe publisher for sending fantasy sports recaps."""
import asyncio
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from config import settings


class GroupMePublisher:
    """Publisher for sending messages to GroupMe groups via bot."""
    
    BASE_URL = "https://api.groupme.com/v3"
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.groupme_access_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def publish_groupme(self, bot_id: str, text: str, attachments: Optional[list] = None) -> bool:
        """
        Send a message to GroupMe via bot.
        
        Args:
            bot_id: GroupMe bot ID
            text: Message text to send
            attachments: Optional attachments (images, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not bot_id or not text:
            print("Missing bot_id or text for GroupMe message")
            return False
        
        # Prepare message payload
        payload = {
            "bot_id": bot_id,
            "text": text[:1000],  # GroupMe has a 1000 character limit
        }
        
        if attachments:
            payload["attachments"] = attachments
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/bots/post",
                json=payload
            )
            
            if response.status_code == 202:
                print(f"Successfully sent message to GroupMe bot {bot_id}")
                return True
            else:
                print(f"Failed to send GroupMe message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending GroupMe message: {e}")
            return False
    
    async def get_bot_info(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a bot."""
        if not self.access_token:
            print("No GroupMe access token configured")
            return None
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/bots",
                params={"token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                bots = data.get("response", [])
                
                for bot in bots:
                    if bot.get("bot_id") == bot_id:
                        return bot
                
                print(f"Bot {bot_id} not found")
                return None
            else:
                print(f"Failed to get bot info: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting bot info: {e}")
            return None
    
    async def create_bot(
        self, 
        group_id: str, 
        name: str, 
        callback_url: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new GroupMe bot.
        
        Args:
            group_id: GroupMe group ID
            name: Bot name
            callback_url: Optional webhook callback URL
            avatar_url: Optional bot avatar image URL
            
        Returns:
            Bot ID if successful, None otherwise
        """
        if not self.access_token:
            print("No GroupMe access token configured")
            return None
        
        payload = {
            "bot": {
                "name": name,
                "group_id": group_id,
            }
        }
        
        if callback_url:
            payload["bot"]["callback_url"] = callback_url
        
        if avatar_url:
            payload["bot"]["avatar_url"] = avatar_url
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/bots",
                params={"token": self.access_token},
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                bot_id = data.get("response", {}).get("bot", {}).get("bot_id")
                print(f"Successfully created bot: {bot_id}")
                return bot_id
            else:
                print(f"Failed to create bot: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating bot: {e}")
            return None
    
    async def destroy_bot(self, bot_id: str) -> bool:
        """Delete a bot."""
        if not self.access_token:
            print("No GroupMe access token configured")
            return False
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/bots/destroy",
                params={"token": self.access_token},
                json={"bot_id": bot_id}
            )
            
            if response.status_code == 200:
                print(f"Successfully deleted bot: {bot_id}")
                return True
            else:
                print(f"Failed to delete bot: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error deleting bot: {e}")
            return False
    
    async def get_groups(self) -> Optional[list]:
        """Get all groups the user belongs to."""
        if not self.access_token:
            print("No GroupMe access token configured")
            return None
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/groups",
                params={"token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", [])
            else:
                print(f"Failed to get groups: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting groups: {e}")
            return None
    
    async def send_with_retry(
        self, 
        bot_id: str, 
        text: str, 
        max_retries: int = 3, 
        delay: float = 1.0
    ) -> bool:
        """
        Send message with retry logic.
        
        Args:
            bot_id: GroupMe bot ID
            text: Message text
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(max_retries + 1):
            success = await self.publish_groupme(bot_id, text)
            
            if success:
                return True
            
            if attempt < max_retries:
                print(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
        
        print(f"Failed to send message after {max_retries + 1} attempts")
        return False
    
    def format_for_groupme(self, text: str, max_length: int = 1000) -> str:
        """
        Format text for GroupMe, respecting character limits.
        
        Args:
            text: Original text
            max_length: Maximum character length (default 1000 for GroupMe)
            
        Returns:
            Formatted text that fits within limits
        """
        if len(text) <= max_length:
            return text
        
        # Try to truncate at a natural break point
        truncated = text[:max_length - 3]  # Leave room for "..."
        
        # Find the last newline or sentence ending
        last_newline = truncated.rfind('\n')
        last_period = truncated.rfind('.')
        last_break = max(last_newline, last_period)
        
        if last_break > max_length * 0.8:  # If break point is reasonable
            return truncated[:last_break + 1] + "..."
        else:
            return truncated + "..."
    
    async def send_long_message(self, bot_id: str, text: str) -> bool:
        """
        Send long messages by splitting them if necessary.
        
        Args:
            bot_id: GroupMe bot ID
            text: Message text (can be longer than GroupMe limit)
            
        Returns:
            bool: True if all parts sent successfully
        """
        if len(text) <= 1000:
            return await self.publish_groupme(bot_id, text)
        
        # Split into multiple messages
        lines = text.split('\n')
        current_message = ""
        messages = []
        
        for line in lines:
            if len(current_message + line + '\n') > 950:  # Leave some buffer
                if current_message:
                    messages.append(current_message.strip())
                current_message = line + '\n'
            else:
                current_message += line + '\n'
        
        if current_message:
            messages.append(current_message.strip())
        
        # Send each part with a small delay
        all_success = True
        for i, message in enumerate(messages):
            if i > 0:
                await asyncio.sleep(0.5)  # Small delay between messages
            
            success = await self.publish_groupme(bot_id, f"({i+1}/{len(messages)}) {message}")
            if not success:
                all_success = False
        
        return all_success


# Convenience function for simple usage
async def send_to_groupme(bot_id: str, text: str) -> bool:
    """
    Simple function to send a message to GroupMe.
    
    Args:
        bot_id: GroupMe bot ID
        text: Message text
        
    Returns:
        bool: True if successful
    """
    publisher = GroupMePublisher()
    try:
        return await publisher.send_with_retry(bot_id, text)
    finally:
        await publisher.close()


# Background task function
async def publish_recap_to_groupme(bot_id: str, recap_text: str):
    """Background task to publish recap to GroupMe."""
    success = await send_to_groupme(bot_id, recap_text)
    if success:
        print(f"Successfully published recap to GroupMe bot {bot_id}")
    else:
        print(f"Failed to publish recap to GroupMe bot {bot_id}")
