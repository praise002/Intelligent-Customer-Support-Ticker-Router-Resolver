import email
import imaplib
import json
import logging
import os
import time
from datetime import datetime
from email.header import decode_header
from typing import Dict, List, Optional

from decouple import config


class EmailPoller:
    """
    Polls email inbox for new support tickets
    Monitors UNSEEN emails and processes them through your workflow
    """

    def __init__(self):
        # Load configuration from environment variables
        self.imap_server = config("IMAP_SERVER", "imap.gmail.com")
        self.email_address = config("MAIL_FROM")
        self.password = config("MAIL_PASSWORD")
        self.poll_interval = int(config("POLL_INTERVAL", "60"))

        # Validate required config
        if not self.email_address or not self.password:
            raise ValueError(
                "EMAIL_ADDRESS and EMAIL_PASSWORD must be set in .env file"
            )

        # Connection state
        self.mail = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5

    def connect(self) -> bool:
        """Establish connection to email server with retry logic"""
        self.connection_attempts += 1

        if self.connection_attempts > self.max_connection_attempts:
            logging.error(
                f"Max connection attempts ({self.max_connection_attempts}) reached"
            )
            return False

        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            logging.info(f"✓ Connected to {self.email_address}")
            self.connection_attempts = 0  # Reset on success
            return True
        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP error: {e}")
            logging.error("Check your credentials and IMAP settings")
            return False
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Safely close email connection"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logging.info("Disconnected")
            except:
                pass
            finally:
                self.mail = None

    def decode_header_value(self, value: str) -> str:
        """Decode email header value (handles encoding)"""
        if not value:
            return ""

        decoded_parts = decode_header(value)
        decoded_string = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_string += part

        return decoded_string

    def extract_email_body(self, msg) -> Dict[str, str]:
        """Extract plain text and HTML body from email message"""
        body = {"plain": "", "html": ""}

        if msg.is_multipart():
            # Email has multiple parts (text, html, attachments)
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                try:
                    part_body = part.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )
                except:
                    continue

                if content_type == "text/plain":
                    body["plain"] += part_body
                elif content_type == "text/html":
                    body["html"] += part_body
        else:
            # Simple email with single part
            content_type = msg.get_content_type()
            try:
                part_body = msg.get_payload(decode=True).decode(
                    "utf-8", errors="ignore"
                )
                if content_type == "text/plain":
                    body["plain"] = part_body
                elif content_type == "text/html":
                    body["html"] = part_body
            except:
                pass

        return body

    def parse_email(self, email_message) -> Dict:
        """Parse raw email into structured ticket data"""

        # Extract headers
        subject = self.decode_header_value(email_message.get("Subject", ""))
        from_header = self.decode_header_value(email_message.get("From", ""))
        to_header = self.decode_header_value(email_message.get("To", ""))
        date_header = email_message.get("Date", "")
        message_id = email_message.get("Message-ID", "")

        # Extract body content
        body = self.extract_email_body(email_message)

        # Extract attachment metadata
        attachments = []
        if email_message.is_multipart():
            for part in email_message.walk():
                if "attachment" in str(part.get("Content-Disposition")):
                    filename = part.get_filename()
                    if filename:
                        attachments.append(
                            {
                                "filename": self.decode_header_value(filename),
                                "content_type": part.get_content_type(),
                                "size": len(part.get_payload(decode=True) or b""),
                            }
                        )

        return {
            "subject": subject,
            "from": from_header,
            "to": to_header,
            "date": date_header,
            "message_id": message_id,
            "body_plain": body["plain"],
            "body_html": body["html"],
            "attachments": attachments,
            "received_at": datetime.now().isoformat(),
        }

    def build_ticket(self):
        """Build TicketInput from IncomingEmail
            TicketInput {
            ticket_id   : generate UUID
            subject     : IncomingEmail.subject
            description : IncomingEmail.body
            priority    : "medium" (default; can be inferred later)
            category    : None (workflow infers it)
        }"""
        # saves it to db
        # when marked as resolved can be changed to is_deleted=True
        # We need to keep it for anlytics
        pass

    def process_ticket(self, ticket_data: Dict):
        """
            Call workflow.process_ticket(ticket_dict)
        Returns:
            action            : "auto_resolve" | "human_review" | "escalate"
            confidence_signals: ConfidenceSignals
            llm_response      : str
            reasoning         : str
            processing_time   : float"""
        pass
    
    def check_new_emails(self) -> int:
        """Check inbox for new unread emails"""
        try:
            # Select inbox folder
            self.mail.select('inbox')
            
            # Search for UNSEEN (unread) emails
            status, messages = self.mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logging.error("Failed to search for emails")
                return 0
            
            email_ids = messages[0].split()
            
            if not email_ids:
                # No new emails
                return 0
            
            logging.info(f"📬 Found {len(email_ids)} new email(s)")
            
            # Process each new email
            for email_id in email_ids:
                try:
                    # Fetch the email
                    status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        logging.error(f"Failed to fetch email {email_id}")
                        continue
                    
                    # Parse the raw email
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract ticket data
                    ticket_data = self.parse_email(email_message)
                    
                    # Process the ticket
                    self.process_ticket(ticket_data)
                    
                    # Optional: Mark as read after processing
                    # Uncomment the line below if you want processed emails marked as read
                    self.mail.store(email_id, '+FLAGS', '\\Seen')
                    
                except Exception as e:
                    logging.error(f"Error processing email {email_id}: {e}")
            
            return len(email_ids)
        except Exception as e:
            logging.error(f"Error checking emails: {e}")
            return 0

    def run(self):
        """Main polling loop - runs continuously checking for new emails"""
        logging.info("🚀 Email Poller Started")
        logging.info(f"📧 Monitoring: {self.email_address}")
        logging.info(f"⏱️  Poll interval: {self.poll_interval}s")
        logging.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Ensure we're connected
                if not self.mail:
                    if not self.connect():
                        logging.warning(f"Retrying connection in 30s...")
                        time.sleep(30)
                        continue
                
                # Check for new emails
                try:
                    count = self.check_new_emails()
                    if count > 0:
                        logging.info(f"✓ Processed {count} ticket(s)\n")
                except Exception as e:
                    logging.error(f"Poll error: {e}")
                    # Disconnect and reconnect on next iteration
                    self.disconnect()
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logging.info("\n🛑 Shutting down...")
            self.disconnect()
            logging.info("Goodbye!")

new = EmailPoller()
new.run()
# logging.warning(
#             "Password reset attempt on invalid/inactive account",
#             extra={
#                 "event_type": "password_reset_invalid_email",
#                 "email": email,
#                 "user_agent": request.headers.get("user-agent"),
#             },
#         )

# logging.exception(f"Google authentication failed: {str(e)}")

# https://www.geeksforgeeks.org/python/how-to-read-emails-from-gmail-using-gmail-api-in-python/
