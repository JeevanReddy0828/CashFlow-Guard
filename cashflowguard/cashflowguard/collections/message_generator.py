"""
Email and SMS template generator for collections outreach.

Generates personalized messages based on:
- Invoice details (amount, days overdue, due date)
- Customer information (name, payment history)
- Risk level (low, medium, high, very_high)
- Action type (reminder, notice, call, escalate, payment_plan)
"""

from datetime import datetime, timedelta
from typing import Dict, Literal
import pandas as pd

ActionType = Literal["friendly_reminder", "second_notice", "call_request", "escalate", "payment_plan", "thank_you"]
RiskLevel = Literal["low", "medium", "high", "very_high"]


class MessageGenerator:
    """Generate personalized collection messages."""
    
    def __init__(self, company_name: str = "Your Company", 
                 company_phone: str = "(555) 123-4567",
                 company_email: str = "accounts@company.com"):
        self.company_name = company_name
        self.company_phone = company_phone
        self.company_email = company_email
    
    def generate_email(
        self,
        customer_name: str,
        invoice_id: str,
        invoice_amount: float,
        due_date: datetime,
        days_overdue: int,
        action_type: ActionType,
        risk_level: RiskLevel,
        payment_link: str = None
    ) -> Dict[str, str]:
        """
        Generate personalized email template.
        
        Returns:
            dict with 'subject' and 'body' keys
        """
        templates = {
            "friendly_reminder": self._friendly_reminder_email,
            "second_notice": self._second_notice_email,
            "call_request": self._call_request_email,
            "escalate": self._escalate_email,
            "payment_plan": self._payment_plan_email,
            "thank_you": self._thank_you_email
        }
        
        template_func = templates.get(action_type, self._friendly_reminder_email)
        
        return template_func(
            customer_name=customer_name,
            invoice_id=invoice_id,
            invoice_amount=invoice_amount,
            due_date=due_date,
            days_overdue=days_overdue,
            risk_level=risk_level,
            payment_link=payment_link
        )
    
    def generate_sms(
        self,
        customer_name: str,
        invoice_id: str,
        invoice_amount: float,
        days_overdue: int,
        action_type: ActionType
    ) -> str:
        """
        Generate SMS message (160 chars max).
        
        Returns:
            SMS text string
        """
        templates = {
            "friendly_reminder": self._friendly_reminder_sms,
            "second_notice": self._second_notice_sms,
            "call_request": self._call_request_sms,
            "escalate": self._escalate_sms,
            "payment_plan": self._payment_plan_sms,
            "thank_you": self._thank_you_sms
        }
        
        template_func = templates.get(action_type, self._friendly_reminder_sms)
        
        return template_func(
            customer_name=customer_name,
            invoice_id=invoice_id,
            invoice_amount=invoice_amount,
            days_overdue=days_overdue
        )
    
    # Email Templates
    
    def _friendly_reminder_email(self, customer_name, invoice_id, invoice_amount, 
                                 due_date, days_overdue, risk_level, payment_link):
        """Friendly payment reminder."""
        subject = f"Friendly Reminder: Invoice #{invoice_id} - ${invoice_amount:,.2f}"
        
        body = f"""Dear {customer_name},

I hope this message finds you well!

This is a friendly reminder that Invoice #{invoice_id} for ${invoice_amount:,.2f} was due on {due_date.strftime('%B %d, %Y')} ({days_overdue} days ago).

We understand that oversights happen, and we wanted to reach out to see if there's anything we can help with regarding this payment.

Invoice Details:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Original Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}

{self._get_payment_instructions(payment_link)}

If you've already sent payment, please disregard this message and accept our thanks! If you have any questions or need to discuss payment options, please don't hesitate to contact us.

Thank you for your business!

Best regards,
Accounts Receivable Team
{self.company_name}
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    def _second_notice_email(self, customer_name, invoice_id, invoice_amount,
                            due_date, days_overdue, risk_level, payment_link):
        """Second notice - more urgent."""
        subject = f"SECOND NOTICE: Invoice #{invoice_id} - Payment Required"
        
        body = f"""Dear {customer_name},

This is our second notice regarding Invoice #{invoice_id} for ${invoice_amount:,.2f}, which is now {days_overdue} days overdue.

We have not yet received payment for this invoice, which was originally due on {due_date.strftime('%B %d, %Y')}.

Outstanding Invoice:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}
• Late Fee (if applicable): Accruing

{self._get_payment_instructions(payment_link)}

IMPORTANT: To avoid any interruption in service or additional late fees, please remit payment within the next 5 business days.

If you are experiencing difficulty making this payment, please contact us immediately to discuss payment arrangement options. We are here to work with you.

If payment has been sent, please reply with payment confirmation details.

Sincerely,
Accounts Receivable Department
{self.company_name}
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    def _call_request_email(self, customer_name, invoice_id, invoice_amount,
                           due_date, days_overdue, risk_level, payment_link):
        """Request for phone call discussion."""
        subject = f"URGENT: Let's Discuss Invoice #{invoice_id} - ${invoice_amount:,.2f}"
        
        body = f"""Dear {customer_name},

We need to discuss Invoice #{invoice_id} for ${invoice_amount:,.2f}, which is now {days_overdue} days past due.

Despite previous communications, this invoice remains unpaid. We would like to speak with you directly to resolve this matter.

Invoice Summary:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}

ACTION REQUIRED:
Please call us at {self.company_phone} within 48 hours to discuss this account. Our office hours are Monday-Friday, 9 AM - 5 PM.

Alternatively, you can reply to this email with a convenient time for us to call you.

We value our business relationship and want to resolve this matter promptly. Payment arrangements may be available if you're experiencing financial difficulties.

Time-Sensitive Matter - Please Respond Immediately

{self.company_name} - Accounts Receivable
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    def _escalate_email(self, customer_name, invoice_id, invoice_amount,
                       due_date, days_overdue, risk_level, payment_link):
        """Final notice before escalation."""
        subject = f"FINAL NOTICE: Invoice #{invoice_id} - Immediate Action Required"
        
        body = f"""Dear {customer_name},

FINAL NOTICE

This is our final attempt to collect payment for Invoice #{invoice_id} before escalating this matter.

Critical Account Status:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Original Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}
• Status: SERIOUSLY DELINQUENT

We have made multiple attempts to contact you regarding this overdue invoice. Unfortunately, we have not received payment or any response to our previous communications.

IMMEDIATE ACTION REQUIRED:
You have 72 hours from receipt of this notice to either:
1. Pay the full amount due, OR
2. Contact us to arrange an approved payment plan

Failure to respond will result in:
• Account suspension/service interruption
• Referral to collections agency
• Negative impact on business credit
• Potential legal action

{self._get_payment_instructions(payment_link)}

We sincerely hope to avoid these measures. Please contact us immediately at {self.company_phone} or reply to this email.

This is a formal notice of debt collection.

{self.company_name}
Collections Department
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    def _payment_plan_email(self, customer_name, invoice_id, invoice_amount,
                           due_date, days_overdue, risk_level, payment_link):
        """Offer payment plan option."""
        subject = f"Payment Plan Available: Invoice #{invoice_id}"
        
        installment = invoice_amount / 3
        
        body = f"""Dear {customer_name},

We understand that businesses sometimes face cash flow challenges. We want to work with you to resolve Invoice #{invoice_id}.

Outstanding Amount: ${invoice_amount:,.2f}
Days Overdue: {days_overdue}

PAYMENT PLAN OFFER:
We can arrange a payment plan to help you clear this balance:

Option 1 - Three Monthly Installments:
• Payment 1: ${installment:,.2f} (Due immediately)
• Payment 2: ${installment:,.2f} (Due in 30 days)
• Payment 3: ${installment:,.2f} (Due in 60 days)

Option 2 - Custom Arrangement:
Contact us to discuss a plan that works for your situation.

To accept this payment plan:
1. Reply to this email confirming your chosen option
2. Make the first payment within 5 business days
3. We'll send you a payment agreement to sign

This is a limited-time offer to help you avoid further collection actions and maintain our business relationship.

Please respond within 48 hours to secure this arrangement.

We're here to help!

Best regards,
{self.company_name}
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    def _thank_you_email(self, customer_name, invoice_id, invoice_amount,
                        due_date, days_overdue, risk_level, payment_link):
        """Thank you for payment."""
        subject = f"Payment Received - Thank You! (Invoice #{invoice_id})"
        
        body = f"""Dear {customer_name},

Thank you! We've received your payment of ${invoice_amount:,.2f} for Invoice #{invoice_id}.

Payment Details:
• Invoice Number: {invoice_id}
• Amount Paid: ${invoice_amount:,.2f}
• Status: PAID IN FULL

Your account is now current. We appreciate your prompt attention to this matter and value your continued business.

If you have any questions about this payment or your account, please don't hesitate to contact us.

Thank you for being a valued customer!

Best regards,
{self.company_name}
{self.company_phone}
{self.company_email}
"""
        return {"subject": subject, "body": body}
    
    # SMS Templates
    
    def _friendly_reminder_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Friendly SMS reminder."""
        return f"{self.company_name}: Hi {customer_name}, friendly reminder Invoice #{invoice_id} (${invoice_amount:,.0f}) is {days_overdue} days past due. Pay at {self.company_email}"
    
    def _second_notice_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Second notice SMS."""
        return f"{self.company_name}: NOTICE: Invoice #{invoice_id} (${invoice_amount:,.0f}) is {days_overdue} days overdue. Please pay immediately or call {self.company_phone}"
    
    def _call_request_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Call request SMS."""
        return f"{self.company_name}: URGENT - Please call us at {self.company_phone} about Invoice #{invoice_id} (${invoice_amount:,.0f}), {days_overdue} days past due"
    
    def _escalate_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Escalation SMS."""
        return f"{self.company_name}: FINAL NOTICE - Invoice #{invoice_id} (${invoice_amount:,.0f}) MUST be paid within 72hrs to avoid collections. Call {self.company_phone}"
    
    def _payment_plan_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Payment plan SMS."""
        return f"{self.company_name}: Payment plan available for Invoice #{invoice_id} (${invoice_amount:,.0f}). Reply YES or call {self.company_phone} to discuss options"
    
    def _thank_you_sms(self, customer_name, invoice_id, invoice_amount, days_overdue):
        """Thank you SMS."""
        return f"{self.company_name}: Payment received! Thank you for paying Invoice #{invoice_id} (${invoice_amount:,.0f}). Your account is current."
    
    # Helper Methods
    
    def _get_payment_instructions(self, payment_link):
        """Generate payment instruction text."""
        instructions = "Payment Options:"
        
        if payment_link:
            instructions += f"\n• Pay Online: {payment_link}"
        
        instructions += f"""
• Bank Transfer: Contact us for ACH details
• Check: Mail to {self.company_name}
• Phone: Call {self.company_phone} to pay by card"""
        
        return instructions
    
    def recommend_action(self, days_overdue: int, risk_score: int, 
                        previous_actions: list = None) -> ActionType:
        """
        Recommend next best action based on context.
        
        Args:
            days_overdue: Number of days past due
            risk_score: Risk score (0-100)
            previous_actions: List of previous action types taken
            
        Returns:
            Recommended action type
        """
        if previous_actions is None:
            previous_actions = []
        
        # Escalation ladder
        if days_overdue <= 7 and risk_score < 50:
            return "friendly_reminder"
        elif days_overdue <= 15 and "friendly_reminder" in previous_actions:
            return "second_notice"
        elif days_overdue <= 30 and "second_notice" in previous_actions:
            if risk_score >= 70:
                return "call_request"
            else:
                return "payment_plan"
        elif days_overdue <= 60 and "call_request" in previous_actions:
            return "payment_plan"
        elif days_overdue > 60 or risk_score >= 90:
            return "escalate"
        else:
            # Default progression
            if not previous_actions:
                return "friendly_reminder"
            elif len(previous_actions) == 1:
                return "second_notice"
            elif len(previous_actions) == 2:
                return "call_request"
            else:
                return "escalate"