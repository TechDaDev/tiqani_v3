"""Contract management models for work agreements, stages, and extensions."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
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
	PLATFORM_FEE_RATE = Decimal('0.10')

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
	client_platform_fee = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		default=Decimal('0.00'),
		help_text="Non-refundable client platform fee charged on contract activation"
	)
	technician_platform_fee = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		default=Decimal('0.00'),
		help_text="Non-refundable technician platform fee charged on contract activation"
	)
	
	# Timeline
	start_date = models.DateField(
		null=True,
		blank=True,
		help_text="Project start date provided by technician"
	)
	duration_days = models.PositiveIntegerField(
		null=True,
		blank=True,
		help_text="Number of days for the project duration"
	)
	contract_duration = models.DateField(
		null=True,
		blank=True,
		help_text="Calculated deadline date (start_date + duration_days)"
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

		# Calculate deadline if start_date and duration are provided
		if self.start_date and self.duration_days:
			self.contract_duration = self.start_date + timedelta(days=self.duration_days)

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
					with transaction.atomic():
						self._setup_contract_escrow()
						# Set technician as unavailable during active contract
						self.technician.is_available = False
						self.technician.save(update_fields=['is_available'])
				except Exception as e:
					# Revert status if escrow setup fails
					self.status = 'pending_acceptance'
					raise e
		
		super().save(*args, **kwargs)

		# Create stages once all required fields are present (even in draft/pending)
		requirements_ready = all([
			self.agreed_amount,
			self.stage_number,
			self.start_date,
			self.duration_days,
			self.contract_duration
		])
		if requirements_ready and self.stages.count() == 0:
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
		if not self.start_date:
			incomplete.append('Start Date')
		if not self.duration_days:
			incomplete.append('Duration Days')
		if not self.contract_duration:
			incomplete.append('Contract Deadline')
		return incomplete

	def _setup_contract_escrow(self):
		"""
		Setup escrow account by creating initial wallet transaction.
		Called when contract moves to in_progress status.
		Locks agreed_amount in client's wallet.
		"""
		if not self.agreed_amount or self.escrow_amount:
			return

		from wallet.models import (
			WalletTransaction,
			PlatformWallet,
			PlatformWalletTransaction,
		)

		client_wallet = self.client.user.wallet
		technician_wallet = self.technician.user.wallet
		platform_wallet = PlatformWallet.get_global_wallet()

		client_fee = (self.agreed_amount * self.PLATFORM_FEE_RATE).quantize(Decimal('0.01'))
		technician_fee = (self.agreed_amount * self.PLATFORM_FEE_RATE).quantize(Decimal('0.01'))
		required_client_amount = self.agreed_amount + client_fee

		if client_wallet.balance < required_client_amount:
			shortfall = required_client_amount - client_wallet.balance
			raise ValueError(
				f"Insufficient client funds for activation. Client needs {required_client_amount} IQD "
				f"(including {client_fee} IQD platform fee), short by {shortfall} IQD."
			)

		if technician_wallet.balance < technician_fee:
			shortfall = technician_fee - technician_wallet.balance
			raise ValueError(
				f"Insufficient technician funds for activation fee. Technician needs {technician_fee} IQD, "
				f"short by {shortfall} IQD."
			)

		# Deduct non-refundable platform fees and client escrow funding
		client_wallet.balance -= required_client_amount
		technician_wallet.balance -= technician_fee
		client_wallet.save(update_fields=['balance', 'updated_at'])
		technician_wallet.save(update_fields=['balance', 'updated_at'])

		self.escrow_amount = self.agreed_amount
		self.client_platform_fee = client_fee
		self.technician_platform_fee = technician_fee

		WalletTransaction.objects.create(
			wallet=client_wallet,
			contract=self,
			transaction_type=WalletTransaction.Type.ESCROW,
			amount=self.escrow_amount,
			amount_usd=self.amount_usd,
			description=f"Escrow for contract {self.contract_reference}"
		)

		WalletTransaction.objects.create(
			wallet=client_wallet,
			contract=self,
			transaction_type=WalletTransaction.Type.PLATFORM_FEE,
			amount=client_fee,
			description=f"Non-refundable client platform fee for contract {self.contract_reference}"
		)

		WalletTransaction.objects.create(
			wallet=technician_wallet,
			contract=self,
			transaction_type=WalletTransaction.Type.PLATFORM_FEE,
			amount=technician_fee,
			description=f"Non-refundable technician platform fee for contract {self.contract_reference}"
		)

		balance_before = platform_wallet.balance
		balance_after_client_fee = balance_before + client_fee
		balance_after_technician_fee = balance_after_client_fee + technician_fee

		platform_wallet.balance = balance_after_technician_fee
		platform_wallet.total_fees_collected += (client_fee + technician_fee)
		platform_wallet.total_client_fees += client_fee
		platform_wallet.total_technician_fees += technician_fee
		platform_wallet.save(update_fields=['balance', 'total_fees_collected', 'total_client_fees', 'total_technician_fees', 'updated_at'])

		PlatformWalletTransaction.objects.create(
			platform_wallet=platform_wallet,
			contract=self,
			source_user=self.client.user,
			source_wallet=client_wallet,
			source_type=PlatformWalletTransaction.SourceType.CLIENT,
			amount=client_fee,
			balance_after=balance_after_client_fee,
			description=f"Client non-refundable platform fee collected for contract {self.contract_reference}"
		)

		PlatformWalletTransaction.objects.create(
			platform_wallet=platform_wallet,
			contract=self,
			source_user=self.technician.user,
			source_wallet=technician_wallet,
			source_type=PlatformWalletTransaction.SourceType.TECHNICIAN,
			amount=technician_fee,
			balance_after=balance_after_technician_fee,
			description=f"Technician non-refundable platform fee collected for contract {self.contract_reference}"
		)

	def _create_contract_stages(self):
		"""
		Create stage entries for the contract.
		Divides total amount and duration across stages (remainder goes to last stage).
		"""
		if not all([self.stage_number, self.agreed_amount, self.start_date, self.duration_days]):
			return

		# Avoid duplicate creation
		if self.stages.exists():
			return

		# Amount distribution
		base_amount = (self.agreed_amount / self.stage_number).quantize(Decimal('0.01'))
		total_assigned = base_amount * (self.stage_number - 1)
		last_amount = self.agreed_amount - total_assigned

		# Duration distribution
		days_base = self.duration_days // self.stage_number
		days_remainder = self.duration_days % self.stage_number

		running_days = 0
		for stage_num in range(1, self.stage_number + 1):
			stage_days = days_base
			if stage_num == self.stage_number:
				stage_days += days_remainder

			# Deadline inclusive of the allocated days for this stage
			running_days += stage_days
			stage_deadline = self.start_date + timedelta(days=running_days - 1)

			amount = last_amount if stage_num == self.stage_number else base_amount

			ContractStage.objects.create(
				contract=self,
				stage_number=stage_num,
				amount=amount,
				deadline=stage_deadline,
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
			from wallet.models import WalletTransaction
			client_wallet = self.client.user.wallet
			client_wallet.balance += self.escrow_amount
			client_wallet.save(update_fields=['balance', 'updated_at'])
			WalletTransaction.objects.create(
				wallet=client_wallet,
				contract=self,
				transaction_type=WalletTransaction.Type.REFUND,
				amount=self.escrow_amount,
				description=f"Escrow refund for canceled contract {self.contract_reference}. Reason: {reason}"
			)
			self.escrow_amount = Decimal('0.00')
			self.save(update_fields=['escrow_amount'])


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
		'wallet.WalletTransaction',
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
		
		with transaction.atomic():
			self.is_approved_by_client = True
			
			# Create payment release transaction
			from wallet.models import WalletTransaction
			technician_wallet = self.contract.technician.user.wallet
			technician_wallet.balance += self.amount
			technician_wallet.save(update_fields=['balance', 'updated_at'])

			transaction = WalletTransaction.objects.create(
				wallet=technician_wallet,
				contract=self.contract,
				transaction_type=WalletTransaction.Type.RELEASE,
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

