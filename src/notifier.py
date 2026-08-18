import logging
import smtplib
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("Notifier")

class TelegramNotifier:
    """
    Interface for handling formatting and dispatching Telegram alerts to the trader.
    """
    def __init__(self, config: dict):
        self.config = config
        tele_params = config.get("notifications", {})
        self.enabled = tele_params.get("telegram_enabled", False)
        self.token = tele_params.get("telegram_bot_token", "")
        self.chat_id = tele_params.get("telegram_chat_id", "")
        
        logger.info(f"TelegramNotifier status: {'ENABLED' if self.enabled else 'DISABLED'} | Chat ID: {self.chat_id}")

    def send_message(self, text: str) -> bool:
        """Sends a text message using the Telegram Bot API."""
        if not self.enabled:
            return False
            
        if not self.token or not self.chat_id:
            logger.warning("TelegramNotifier is enabled but bot token or chat ID is missing in configuration.")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Sending message to Telegram Chat {self.chat_id}...")
            with urllib.request.urlopen(req, timeout=10) as response:
                res = response.read()
                logger.info("Telegram notification successfully sent.")
                return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_daily_scan_report(self, scan_date_str: str, posture: str, health_score: int, strict_list: list, flex_list: list, mini_list: list = None, paper_engine=None) -> bool:
        """Formats and dispatches the EOD watchlist and portfolio summary via Telegram."""
        html_lines = []
        html_lines.append(f"<b>Daily Minervini Scan - {scan_date_str}</b>")
        html_lines.append(f"Posture: <b>{posture}</b> (Score: {health_score}/10)")
        html_lines.append("")
        
        html_lines.append("<b>STRICT Watchlist:</b>")
        if strict_list:
            for c in strict_list:
                html_lines.append(f"• <code>{c['Symbol']}</code>: Score {c['Score']} | Pivot ₹{c['Pivot Price']:.1f}")
        else:
            html_lines.append("• <i>None</i>")
            
        html_lines.append("")
        html_lines.append("<b>FLEX Watchlist:</b>")
        if flex_list:
            for c in flex_list:
                html_lines.append(f"• <code>{c['Symbol']}</code>: Score {c['Score']} | Pivot ₹{c['Pivot Price']:.1f}")
        else:
            html_lines.append("• <i>None</i>")
            
        html_lines.append("")
        html_lines.append("<b>MINI Watchlist:</b>")
        if mini_list:
            for c in mini_list:
                html_lines.append(f"• <code>{c['Symbol']}</code>: Score {c['Score']} | Pivot ₹{c['Pivot Price']:.1f}")
        else:
            html_lines.append("• <i>None</i>")
            
        if paper_engine:
            cash = paper_engine.state.get("cash", 1000000.0)
            active = len(paper_engine.state.get("active_trades", {}))
            html_lines.append("")
            html_lines.append("<b>Portfolio:</b>")
            html_lines.append(f"• Cash: ₹{cash:,.2f}")
            html_lines.append(f"• Active Positions: {active}")

        text = "\n".join(html_lines)
        return self.send_message(text)

    def send_watchlist_notification(self, candidates: list) -> bool:
        """Fallback compatibility for the original scanner call."""
        text = f"<b>Daily VCP Candidates found:</b>\n" + "\n".join([f"• <code>{sym}</code>" for sym in candidates])
        return self.send_message(text)

    def send_breakout_alert(self, alert_payload: dict) -> bool:
        """Dispatches a real-time breakout alert detailing the entry setup."""
        text = (
            f"🔔 <b>BREAKOUT ALERT: {alert_payload.get('ticker')}</b>\n"
            f"Entry: ₹{alert_payload.get('entry_price'):.2f}\n"
            f"Stop Loss: ₹{alert_payload.get('stop_loss'):.2f}\n"
            f"Suggested Size: {alert_payload.get('position_size')} shares"
        )
        return self.send_message(text)


class EmailNotifier:
    """
    Interface for handling formatting and dispatching email reports via SMTP.
    """
    def __init__(self, config: dict):
        self.config = config
        email_params = config.get("notifications", {})
        self.enabled = email_params.get("email_enabled", False)
        self.smtp_host = email_params.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = email_params.get("smtp_port", 587)
        self.smtp_user = email_params.get("smtp_user", "")
        self.smtp_password = email_params.get("smtp_password", "")
        self.recipient = email_params.get("recipient_email", "vishalthakker2009@gmail.com")
        
        logger.info(f"EmailNotifier status: {'ENABLED' if self.enabled else 'DISABLED'} | Recipient: {self.recipient}")

    def send_report(self, subject: str, html_content: str) -> bool:
        """Sends an HTML email report using SMTP."""
        if not self.enabled:
            return False
            
        if not self.smtp_user or not self.smtp_password:
            logger.warning("EmailNotifier is enabled but SMTP user or password credentials are not set in config/config.yaml.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = self.recipient

            part = MIMEText(html_content, "html")
            msg.attach(part)

            logger.info(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}...")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, self.recipient, msg.as_string())
            server.quit()
            
            logger.info(f"Email notification successfully sent to {self.recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification to {self.recipient}: {e}")
            return False
