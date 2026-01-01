"""Contract management models for work agreements, stages, and extensions."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# --- Base Abstract Models ---

class TimestampedModel(models.Model):
	"""Centralizes ID, soft-delete, and timestamp logic."""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	is_delete = models.BooleanField(default=False, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


# --- Contract Models ---

class Contract(TimestampedModel):
	"""
	Contract model for managing work agreements between clients and technicians.
	Tracks stages, payments, and status throughout the service delivery lifecycle.
	"""
	
	CONTRACT_STATUS = [
		('draft', 'Draft'),
		('pending_acceptance', 'Pending Acceptance'),
		('in_progress', 'In Progress'),
		('completed', 'Completed'),
		('canceled', 'Canceled')
	]

	STAGE_CHOICES = [
		(2, '2 Stages'),
		(3, '3 Stages'),
		(4, '4 Stages'),
		(5, '5 Stages'),
	]

	# Relations
	client = models.ForeignKey(
		'accounts.ClientProfile',
		on_delete=models.CASCADE,
		related_name='contracts',
		help_text="Client initiating the contract"
	)
	technician = models.ForeignKey(
		'accounts.TechnicianProfile',
		on_delete=models.CASCADE,
		related_name='contracts',
		help_text="Technician performing the work"
	)
	
	# Reference & Identification
	contract_reference = models.CharField(
		max_length=20,
		unique=True,
		blank=True,
		help_text="Auto-generated unique contract reference (e.g., #A1B2C3D4E5F6)"
	)
	
	# Contract Details
	work_description = models.TextField(
		null=True,
		blank=True,
		help_text="Detailed description of work to be performed"
	)
	
	# Financial Fields (All in IQD - Iraqi Dinar)
	agreed_amount = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		null=True,
		blank=True,
		help_text="Total agreed amount in IQD (required before acceptance)"
	)
	amount_usd = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		null=True,
		blank=True,
		help_text="USD equivalent for reference only"
	)
	exchange_rate = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		null=True,
		blank=True,
		help_text="Exchange rate (IQD to USD) recorded at contract creation"
	)
	currency = models.CharField(
		max_length=3,
		default='IQD',
		help_text="Currency code for agreed amount"
	)
	escrow_amount = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		default=Decimal('0.00'),
		help_text="Amount held in escrow in IQD"
	)
	total_paid = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		default=Decimal('0.00'),
		help_text="Total amount paid to technician so far in IQD"
	)
	
	# Timeline
	contract_duration = models.DateField(
		null=True,
		blank=True,
		help_text="Expected completion date"
	)
	
	# Workflow & Status
	status = models.CharField(
		max_length=50,
		choices=CONTRACT_STATUS,
		default='draft',
		db_index=True,
		help_text="Current contract status"
	)
	stage_number = models.PositiveSmallIntegerField(
		choices=STAGE_CHOICES,
		null=True,
		blank=True,
		help_text="Number of payment stages for this contract"
	)
	
	# Acceptance Tracking
	client_accepted = models.BooleanField(
		default=False,
		db_index=True,
		help_text="Client has accepted the contract"
	)
	technician_accepted = models.BooleanField(
		default=False,
		db_index=True,
		help_text="Technician has accepted the contract"
	)

	class Meta:
		"""
		Database indexing and ordering for efficient contract queries.
		Indexes optimize filtering by client, technician, status, and acceptance status.
		"""
		indexes = [
			models.Index(fields=['client']),
			models.Index(fields=['technician']),
			models.Index(fields=['status']),
			models.Index(fields=['client_accepted', 'technician_accepted']),
			models.Index(fields=['created_at']),
			models.Index(fields=['is_delete']),
		]
		ordering = ['-created_at']
		verbose_name = 'Contract'
		verbose_name_plural = 'Contracts'

	def __str__(self):
		"""Return contract representation with reference and status."""
		status_display = dict(self.CONTRACT_STATUS).get(self.status, self.status)
		return f"Contract {self.contract_reference} - {status_display}"

	def save(self, *args, **kwargs):
		"""
		Auto-generate contract reference and handle status transitions.
		Ensures data consistency before saving.
		
		Status Flow:
		- draft → pending_acceptance (when technician adds amount/stages)
		- pending_acceptance → in_progress (when both parties accept)
		- in_progress → completed (when all stages approved)
		"""
		# Generate contract reference if not present
		if not self.contract_reference:
			self.contract_reference = self.generate_contract_reference()
		
		# Get old status for transition logic
		old_status = None
		if self.pk:
			try:
				old_status = Contract.objects.get(pk=self.pk).status
			except Contract.DoesNotExist:
				pass
		
		# Auto-transition to pending_acceptance when all required fields are filled
		if (self.status == 'draft' and
			all([self.agreed_amount, self.stage_number, self.work_description, self.contract_duration])):
			self.status = 'pending_acceptance'
		
		# Validate required fields for pending_acceptance
		if self.status == 'pending_acceptance':
			if not all([self.agreed_amount, self.stage_number, self.work_description, self.contract_duration]):
				raise ValueError("Contract must have amount, stages, description and duration before acceptance")
		
		# Check if both parties accepted to move to in_progress
		if (self.client_accepted and self.technician_accepted and
			self.status == 'pending_acceptance'):
			self.status = 'in_progress'
			
			# Setup escrow if transitioning from pending_acceptance
			if old_status == 'pending_acceptance':
				try:
					self._setup_contract_escrow()
					# Set technician as unavailable during active contract
					self.technician.is_available = False
					self.technician.save(update_fields=['is_available'])
				except Exception as e:
					# Revert status if escrow setup fails
					self.status = 'pending_acceptance'
					raise e
		
		super().save(*args, **kwargs)
		
		# Create stages after contract is saved (ensures contract has an ID)
		if (self.status == 'in_progress' and old_status == 'pending_acceptance'):
			self._create_contract_stages()

	def generate_contract_reference(self):
		"""
		Generate a unique contract reference number.
		Format: #XXXXXXXXXXXXX (12 uppercase hex characters)
		"""
		return f"#{uuid.uuid4().hex[:12].upper()}"

	def can_be_accepted(self):
		"""
		Check if contract has all required fields for acceptance.
		Returns boolean indicating if contract is ready for both parties to accept.
		"""
		return all([
			self.agreed_amount,
			self.stage_number,
			self.work_description,
			self.contract_duration
		])

	def get_incomplete_fields(self):
		"""
		Return list of incomplete required fields for contract acceptance.
		Useful for form validation feedback and API responses.
		"""
		incomplete = []
		if not self.agreed_amount:
			incomplete.append('Agreed Amount')
		if not self.stage_number:
			incomplete.append('Stage Number')
		if not self.work_description:
			incomplete.append('Work Description')
		if not self.contract_duration:
			incomplete.append('Contract Duration')
		return incomplete

	def _setup_contract_escrow(self):
		"""
		Setup escrow account by creating initial wallet transaction.
		Called when contract moves to in_progress status.
		Locks agreed_amount in client's wallet.
		"""
		if self.agreed_amount and not self.escrow_amount:
			# Set escrow amount (typically equals agreed amount)
			self.escrow_amount = self.agreed_amount
			
			# Create escrow transaction in client's wallet
			from accounts.models import WalletTransaction
			WalletTransaction.objects.create(
				wallet=self.client.user.wallet,
				contract=self,
				transaction_type='escrow',
				amount=self.escrow_amount,
				amount_usd=self.amount_usd,
				exchange_rate=self.exchange_rate,
				description=f"Escrow for contract {self.contract_reference}"
			)

	def _create_contract_stages(self):
		"""
		Create stage entries for the contract.
		Divides total amount equally among stages.
		Called when contract transitions to in_progress.
		"""
		if not self.stage_number or not self.agreed_amount:
			return
		
		# Calculate amount per stage
		amount_per_stage = self.agreed_amount / self.stage_number
		
		# Create stages
		for stage_num in range(1, self.stage_number + 1):
			ContractStage.objects.create(
				contract=self,
				stage_number=stage_num,
				amount=amount_per_stage,
			)

	def mark_completed(self):
		"""
		Mark contract as completed and release technician availability.
		Called when all stages are approved by client.
		"""
		self.status = 'completed'
		self.technician.is_available = True
		self.technician.save(update_fields=['is_available'])
		self.save(update_fields=['status'])

	def cancel(self, reason=''):
		"""
		Cancel contract and reverse escrow.
		Logs cancellation reason and refunds escrow amount.
		"""
		if self.status in ['completed', 'canceled']:
			status_display = dict(self.CONTRACT_STATUS).get(self.status, self.status)
			raise ValueError(f"Cannot cancel a {status_display} contract")
		
		self.status = 'canceled'
		self.technician.is_available = True
		self.technician.save(update_fields=['is_available'])
		self.save(update_fields=['status'])
		
		# Create cancellation transaction (refund escrow)
		if self.escrow_amount > 0:
			from accounts.models import WalletTransaction
			WalletTransaction.objects.create(
				wallet=self.client.user.wallet,
				contract=self,
				transaction_type='refund',
				amount=self.escrow_amount,
				description=f"Escrow refund for canceled contract {self.contract_reference}. Reason: {reason}"
			)


class ContractStage(TimestampedModel):
	"""
	Individual work stages within a contract.
	Breaks down contract work into milestones with associated payments.
	Each stage represents a deliverable with a deadline and payment.
	"""
	
	contract = models.ForeignKey(
		Contract,
		on_delete=models.CASCADE,
		related_name='stages',
		help_text="Parent contract"
	)
	stage_number = models.PositiveIntegerField(
		help_text="Sequential stage number (1, 2, 3, etc.)"
	)
	stage_description = models.TextField(
		blank=True,
		help_text="Description of work and deliverables for this stage"
	)
	amount = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		help_text="Payment amount for this stage in IQD"
	)
	deadline = models.DateField(
		null=True,
		blank=True,
		help_text="Target completion date for this stage"
	)
	is_approved_by_client = models.BooleanField(
		default=False,
		db_index=True,
		help_text="Client has approved completion of this stage"
	)
	completed_at = models.DateTimeField(
		null=True,
		blank=True,
		help_text="When technician marked this stage as complete"
	)
	transaction = models.OneToOneField(
		'accounts.WalletTransaction',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='contract_stage',
		help_text="Associated payment transaction for this stage"
	)

	class Meta:
		"""
		Index on contract and stage_number for efficient ordering.
		Order by stage number for natural progression.
		Enforce unique stage numbers per contract.
		"""
		indexes = [
			models.Index(fields=['contract', 'stage_number']),
			models.Index(fields=['is_approved_by_client']),
			models.Index(fields=['created_at']),
		]
		ordering = ['contract', 'stage_number']
		unique_together = [('contract', 'stage_number')]
		verbose_name = 'Contract Stage'
		verbose_name_plural = 'Contract Stages'

	def __str__(self):
		"""Return stage representation with contract reference and number."""
		return f"Stage {self.stage_number} of contract {self.contract.contract_reference}"

	def save(self, *args, **kwargs):
		"""Auto-assign stage number if not provided."""
		if not self.stage_number:
			# Get the next stage number for this contract
			existing_stages = ContractStage.objects.filter(
				contract=self.contract
			).count()
			self.stage_number = existing_stages + 1
		
		super().save(*args, **kwargs)

	def mark_complete(self):
		"""Mark stage as completed by technician."""
		self.completed_at = timezone.now()
		self.save(update_fields=['completed_at'])

	def approve_by_client(self):
		"""
		Approve stage completion and release payment.
		Creates wallet transaction for stage payment (minus platform fee).
		Updates contract total_paid counter.
		"""
		if self.is_approved_by_client:
			raise ValueError("This stage has already been approved")
		
		self.is_approved_by_client = True
		
		# Create payment release transaction
		from accounts.models import WalletTransaction
		transaction = WalletTransaction.objects.create(
			wallet=self.contract.technician.user.wallet,
			contract=self.contract,
			transaction_type='release',
			amount=self.amount,
			description=f"Payment release for stage {self.stage_number} of contract {self.contract.contract_reference}"
		)
		
		self.transaction = transaction
		self.save(update_fields=['is_approved_by_client', 'transaction'])
		
		# Update contract total_paid
		self.contract.total_paid += self.amount
		self.contract.save(update_fields=['total_paid'])


class TimeExtensionRequest(TimestampedModel):
	"""
	Request to extend contract deadline.
	Technician requests extension with reason; client approves or rejects.
	If approved, technician distributes additional days to specific stages.
	"""
	
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('approved', 'Approved'),
		('rejected', 'Rejected')
	]
	
	contract = models.ForeignKey(
		Contract,
		on_delete=models.CASCADE,
		related_name='extension_requests',
		help_text="Contract being extended"
	)
	requested_by = models.ForeignKey(
		'accounts.TechnicianProfile',
		on_delete=models.CASCADE,
		related_name='extension_requests',
		help_text="Technician requesting the extension"
	)
	requested_days = models.PositiveSmallIntegerField(
		help_text="Number of days requested (1-30)"
	)
	reason = models.TextField(
		help_text="Reason for requesting the extension"
	)
	status = models.CharField(
		max_length=20,
		choices=STATUS_CHOICES,
		default='pending',
		db_index=True,
		help_text="Current status of the extension request"
	)
	client_response = models.TextField(
		blank=True,
		null=True,
		help_text="Client's response comment or rejection reason"
	)
	responded_at = models.DateTimeField(
		null=True,
		blank=True,
		help_text="When client responded to the request"
	)

	class Meta:
		"""
		Index on status and created_at for efficient filtering and sorting.
		Order by creation date (newest first).
		"""
		indexes = [
			models.Index(fields=['contract', 'status']),
			models.Index(fields=['requested_by', 'status']),
			models.Index(fields=['created_at']),
		]
		ordering = ['-created_at']
		verbose_name = 'Time Extension Request'
		verbose_name_plural = 'Time Extension Requests'

	def __str__(self):
		"""Return extension request representation."""
		return f"Extension request of {self.requested_days} days for contract {self.contract.contract_reference}"

	def clean(self):
		"""Validate extension request business logic."""
		# Validate requested days (1-30)
		if self.requested_days < 1 or self.requested_days > 30:
			raise ValidationError("Extension request must be between 1 and 30 days")
		
		# Ensure technician is assigned to this contract
		if self.requested_by != self.contract.technician:
			raise ValidationError("Only the assigned technician can request extensions")
		
		# Ensure contract is in progress
		if self.contract.status != 'in_progress':
			raise ValidationError("Extensions can only be requested for in-progress contracts")
		
		# Ensure technician doesn't have another pending extension for this contract
		if self.status == 'pending' and not self.pk:
			existing_pending = TimeExtensionRequest.objects.filter(
				requested_by=self.requested_by,
				contract=self.contract,
				status='pending'
			).exists()
			if existing_pending:
				raise ValidationError("You already have a pending extension request for this contract. Please wait for it to be processed.")

	def approve(self, client_response=''):
		"""
		Approve the extension request.
		Saves client's approval comment.
		Does NOT update contract deadline (technician distributes days later).
		"""
		if self.status != 'pending':
			raise ValueError("Only pending extension requests can be approved")
		
		self.status = 'approved'
		self.client_response = client_response
		self.responded_at = timezone.now()
		self.save(update_fields=['status', 'client_response', 'responded_at'])

	def reject(self, rejection_reason=''):
		"""
		Reject the extension request.
		Saves rejection reason from client.
		"""
		if self.status != 'pending':
			raise ValueError("Only pending extension requests can be rejected")
		
		self.status = 'rejected'
		self.client_response = rejection_reason
		self.responded_at = timezone.now()
		self.save(update_fields=['status', 'client_response', 'responded_at'])

