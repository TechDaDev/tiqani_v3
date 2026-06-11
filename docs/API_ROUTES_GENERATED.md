# API Routes — tiqani_v3 (auto-generated)

Total routes: 297

| # | Route | Name | View |
|---|-------|------|------|
| 1 | `admin/` | index | `index` |
| 2 | `admin/login/` | login | `login` |
| 3 | `admin/logout/` | logout | `logout` |
| 4 | `admin/password_change/` | password_change | `password_change` |
| 5 | `admin/password_change/done/` | password_change_done | `password_change_done` |
| 6 | `admin/autocomplete/` | autocomplete | `autocomplete_view` |
| 7 | `admin/jsi18n/` | jsi18n | `i18n_javascript` |
| 8 | `admin/r/<path:content_type_id>/<path:object_id>/` | view_on_site | `shortcut` |
| 9 | `admin/auth/group/` | auth_group_changelist | `changelist_view` |
| 10 | `admin/auth/group/add/` | auth_group_add | `add_view` |
| 11 | `admin/auth/group/<path:object_id>/history/` | auth_group_history | `history_view` |
| 12 | `admin/auth/group/<path:object_id>/delete/` | auth_group_delete | `delete_view` |
| 13 | `admin/auth/group/<path:object_id>/change/` | auth_group_change | `change_view` |
| 14 | `admin/auth/group/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 15 | `admin/token_blacklist/outstandingtoken/` | token_blacklist_outstandingtoken_changelist | `changelist_view` |
| 16 | `admin/token_blacklist/outstandingtoken/add/` | token_blacklist_outstandingtoken_add | `add_view` |
| 17 | `admin/token_blacklist/outstandingtoken/<path:object_id>/history/` | token_blacklist_outstandingtoken_history | `history_view` |
| 18 | `admin/token_blacklist/outstandingtoken/<path:object_id>/delete/` | token_blacklist_outstandingtoken_delete | `delete_view` |
| 19 | `admin/token_blacklist/outstandingtoken/<path:object_id>/change/` | token_blacklist_outstandingtoken_change | `change_view` |
| 20 | `admin/token_blacklist/outstandingtoken/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 21 | `admin/token_blacklist/blacklistedtoken/` | token_blacklist_blacklistedtoken_changelist | `changelist_view` |
| 22 | `admin/token_blacklist/blacklistedtoken/add/` | token_blacklist_blacklistedtoken_add | `add_view` |
| 23 | `admin/token_blacklist/blacklistedtoken/<path:object_id>/history/` | token_blacklist_blacklistedtoken_history | `history_view` |
| 24 | `admin/token_blacklist/blacklistedtoken/<path:object_id>/delete/` | token_blacklist_blacklistedtoken_delete | `delete_view` |
| 25 | `admin/token_blacklist/blacklistedtoken/<path:object_id>/change/` | token_blacklist_blacklistedtoken_change | `change_view` |
| 26 | `admin/token_blacklist/blacklistedtoken/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 27 | `admin/accounts/customuser/<id>/password/` | auth_user_password_change | `user_change_password` |
| 28 | `admin/accounts/customuser/` | accounts_customuser_changelist | `changelist_view` |
| 29 | `admin/accounts/customuser/add/` | accounts_customuser_add | `add_view` |
| 30 | `admin/accounts/customuser/<path:object_id>/history/` | accounts_customuser_history | `history_view` |
| 31 | `admin/accounts/customuser/<path:object_id>/delete/` | accounts_customuser_delete | `delete_view` |
| 32 | `admin/accounts/customuser/<path:object_id>/change/` | accounts_customuser_change | `change_view` |
| 33 | `admin/accounts/customuser/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 34 | `admin/accounts/technicianprofile/` | accounts_technicianprofile_changelist | `changelist_view` |
| 35 | `admin/accounts/technicianprofile/add/` | accounts_technicianprofile_add | `add_view` |
| 36 | `admin/accounts/technicianprofile/<path:object_id>/history/` | accounts_technicianprofile_history | `history_view` |
| 37 | `admin/accounts/technicianprofile/<path:object_id>/delete/` | accounts_technicianprofile_delete | `delete_view` |
| 38 | `admin/accounts/technicianprofile/<path:object_id>/change/` | accounts_technicianprofile_change | `change_view` |
| 39 | `admin/accounts/technicianprofile/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 40 | `admin/accounts/clientprofile/` | accounts_clientprofile_changelist | `changelist_view` |
| 41 | `admin/accounts/clientprofile/add/` | accounts_clientprofile_add | `add_view` |
| 42 | `admin/accounts/clientprofile/<path:object_id>/history/` | accounts_clientprofile_history | `history_view` |
| 43 | `admin/accounts/clientprofile/<path:object_id>/delete/` | accounts_clientprofile_delete | `delete_view` |
| 44 | `admin/accounts/clientprofile/<path:object_id>/change/` | accounts_clientprofile_change | `change_view` |
| 45 | `admin/accounts/clientprofile/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 46 | `admin/accounts/adminprofile/` | accounts_adminprofile_changelist | `changelist_view` |
| 47 | `admin/accounts/adminprofile/add/` | accounts_adminprofile_add | `add_view` |
| 48 | `admin/accounts/adminprofile/<path:object_id>/history/` | accounts_adminprofile_history | `history_view` |
| 49 | `admin/accounts/adminprofile/<path:object_id>/delete/` | accounts_adminprofile_delete | `delete_view` |
| 50 | `admin/accounts/adminprofile/<path:object_id>/change/` | accounts_adminprofile_change | `change_view` |
| 51 | `admin/accounts/adminprofile/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 52 | `admin/wallet/wallet/` | wallet_wallet_changelist | `changelist_view` |
| 53 | `admin/wallet/wallet/add/` | wallet_wallet_add | `add_view` |
| 54 | `admin/wallet/wallet/<path:object_id>/history/` | wallet_wallet_history | `history_view` |
| 55 | `admin/wallet/wallet/<path:object_id>/delete/` | wallet_wallet_delete | `delete_view` |
| 56 | `admin/wallet/wallet/<path:object_id>/change/` | wallet_wallet_change | `change_view` |
| 57 | `admin/wallet/wallet/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 58 | `admin/wallet/wallettransaction/` | wallet_wallettransaction_changelist | `changelist_view` |
| 59 | `admin/wallet/wallettransaction/add/` | wallet_wallettransaction_add | `add_view` |
| 60 | `admin/wallet/wallettransaction/<path:object_id>/history/` | wallet_wallettransaction_history | `history_view` |
| 61 | `admin/wallet/wallettransaction/<path:object_id>/delete/` | wallet_wallettransaction_delete | `delete_view` |
| 62 | `admin/wallet/wallettransaction/<path:object_id>/change/` | wallet_wallettransaction_change | `change_view` |
| 63 | `admin/wallet/wallettransaction/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 64 | `admin/wallet/platformwallet/` | wallet_platformwallet_changelist | `changelist_view` |
| 65 | `admin/wallet/platformwallet/add/` | wallet_platformwallet_add | `add_view` |
| 66 | `admin/wallet/platformwallet/<path:object_id>/history/` | wallet_platformwallet_history | `history_view` |
| 67 | `admin/wallet/platformwallet/<path:object_id>/delete/` | wallet_platformwallet_delete | `delete_view` |
| 68 | `admin/wallet/platformwallet/<path:object_id>/change/` | wallet_platformwallet_change | `change_view` |
| 69 | `admin/wallet/platformwallet/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 70 | `admin/wallet/platformwallettransaction/` | wallet_platformwallettransaction_changelist | `changelist_view` |
| 71 | `admin/wallet/platformwallettransaction/add/` | wallet_platformwallettransaction_add | `add_view` |
| 72 | `admin/wallet/platformwallettransaction/<path:object_id>/history/` | wallet_platformwallettransaction_history | `history_view` |
| 73 | `admin/wallet/platformwallettransaction/<path:object_id>/delete/` | wallet_platformwallettransaction_delete | `delete_view` |
| 74 | `admin/wallet/platformwallettransaction/<path:object_id>/change/` | wallet_platformwallettransaction_change | `change_view` |
| 75 | `admin/wallet/platformwallettransaction/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 76 | `admin/accounts/otpverification/` | accounts_otpverification_changelist | `changelist_view` |
| 77 | `admin/accounts/otpverification/add/` | accounts_otpverification_add | `add_view` |
| 78 | `admin/accounts/otpverification/<path:object_id>/history/` | accounts_otpverification_history | `history_view` |
| 79 | `admin/accounts/otpverification/<path:object_id>/delete/` | accounts_otpverification_delete | `delete_view` |
| 80 | `admin/accounts/otpverification/<path:object_id>/change/` | accounts_otpverification_change | `change_view` |
| 81 | `admin/accounts/otpverification/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 82 | `admin/accounts/technicianskillset/` | accounts_technicianskillset_changelist | `changelist_view` |
| 83 | `admin/accounts/technicianskillset/add/` | accounts_technicianskillset_add | `add_view` |
| 84 | `admin/accounts/technicianskillset/<path:object_id>/history/` | accounts_technicianskillset_history | `history_view` |
| 85 | `admin/accounts/technicianskillset/<path:object_id>/delete/` | accounts_technicianskillset_delete | `delete_view` |
| 86 | `admin/accounts/technicianskillset/<path:object_id>/change/` | accounts_technicianskillset_change | `change_view` |
| 87 | `admin/accounts/technicianskillset/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 88 | `admin/accounts/technicianimage/` | accounts_technicianimage_changelist | `changelist_view` |
| 89 | `admin/accounts/technicianimage/add/` | accounts_technicianimage_add | `add_view` |
| 90 | `admin/accounts/technicianimage/<path:object_id>/history/` | accounts_technicianimage_history | `history_view` |
| 91 | `admin/accounts/technicianimage/<path:object_id>/delete/` | accounts_technicianimage_delete | `delete_view` |
| 92 | `admin/accounts/technicianimage/<path:object_id>/change/` | accounts_technicianimage_change | `change_view` |
| 93 | `admin/accounts/technicianimage/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 94 | `admin/category/category/` | category_category_changelist | `changelist_view` |
| 95 | `admin/category/category/add/` | category_category_add | `add_view` |
| 96 | `admin/category/category/<path:object_id>/history/` | category_category_history | `history_view` |
| 97 | `admin/category/category/<path:object_id>/delete/` | category_category_delete | `delete_view` |
| 98 | `admin/category/category/<path:object_id>/change/` | category_category_change | `change_view` |
| 99 | `admin/category/category/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 100 | `admin/category/skill/` | category_skill_changelist | `changelist_view` |
| 101 | `admin/category/skill/add/` | category_skill_add | `add_view` |
| 102 | `admin/category/skill/<path:object_id>/history/` | category_skill_history | `history_view` |
| 103 | `admin/category/skill/<path:object_id>/delete/` | category_skill_delete | `delete_view` |
| 104 | `admin/category/skill/<path:object_id>/change/` | category_skill_change | `change_view` |
| 105 | `admin/category/skill/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 106 | `admin/category/subskill/` | category_subskill_changelist | `changelist_view` |
| 107 | `admin/category/subskill/add/` | category_subskill_add | `add_view` |
| 108 | `admin/category/subskill/<path:object_id>/history/` | category_subskill_history | `history_view` |
| 109 | `admin/category/subskill/<path:object_id>/delete/` | category_subskill_delete | `delete_view` |
| 110 | `admin/category/subskill/<path:object_id>/change/` | category_subskill_change | `change_view` |
| 111 | `admin/category/subskill/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 112 | `admin/contract/contract/` | contract_contract_changelist | `changelist_view` |
| 113 | `admin/contract/contract/add/` | contract_contract_add | `add_view` |
| 114 | `admin/contract/contract/<path:object_id>/history/` | contract_contract_history | `history_view` |
| 115 | `admin/contract/contract/<path:object_id>/delete/` | contract_contract_delete | `delete_view` |
| 116 | `admin/contract/contract/<path:object_id>/change/` | contract_contract_change | `change_view` |
| 117 | `admin/contract/contract/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 118 | `admin/contract/contractstage/` | contract_contractstage_changelist | `changelist_view` |
| 119 | `admin/contract/contractstage/add/` | contract_contractstage_add | `add_view` |
| 120 | `admin/contract/contractstage/<path:object_id>/history/` | contract_contractstage_history | `history_view` |
| 121 | `admin/contract/contractstage/<path:object_id>/delete/` | contract_contractstage_delete | `delete_view` |
| 122 | `admin/contract/contractstage/<path:object_id>/change/` | contract_contractstage_change | `change_view` |
| 123 | `admin/contract/contractstage/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 124 | `admin/contract/timeextensionrequest/` | contract_timeextensionrequest_changelist | `changelist_view` |
| 125 | `admin/contract/timeextensionrequest/add/` | contract_timeextensionrequest_add | `add_view` |
| 126 | `admin/contract/timeextensionrequest/<path:object_id>/history/` | contract_timeextensionrequest_history | `history_view` |
| 127 | `admin/contract/timeextensionrequest/<path:object_id>/delete/` | contract_timeextensionrequest_delete | `delete_view` |
| 128 | `admin/contract/timeextensionrequest/<path:object_id>/change/` | contract_timeextensionrequest_change | `change_view` |
| 129 | `admin/contract/timeextensionrequest/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 130 | `admin/ratereview/review/` | ratereview_review_changelist | `changelist_view` |
| 131 | `admin/ratereview/review/add/` | ratereview_review_add | `add_view` |
| 132 | `admin/ratereview/review/<path:object_id>/history/` | ratereview_review_history | `history_view` |
| 133 | `admin/ratereview/review/<path:object_id>/delete/` | ratereview_review_delete | `delete_view` |
| 134 | `admin/ratereview/review/<path:object_id>/change/` | ratereview_review_change | `change_view` |
| 135 | `admin/ratereview/review/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 136 | `admin/ratereview/reviewhelpful/` | ratereview_reviewhelpful_changelist | `changelist_view` |
| 137 | `admin/ratereview/reviewhelpful/add/` | ratereview_reviewhelpful_add | `add_view` |
| 138 | `admin/ratereview/reviewhelpful/<path:object_id>/history/` | ratereview_reviewhelpful_history | `history_view` |
| 139 | `admin/ratereview/reviewhelpful/<path:object_id>/delete/` | ratereview_reviewhelpful_delete | `delete_view` |
| 140 | `admin/ratereview/reviewhelpful/<path:object_id>/change/` | ratereview_reviewhelpful_change | `change_view` |
| 141 | `admin/ratereview/reviewhelpful/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 142 | `admin/ratereview/reviewreport/` | ratereview_reviewreport_changelist | `changelist_view` |
| 143 | `admin/ratereview/reviewreport/add/` | ratereview_reviewreport_add | `add_view` |
| 144 | `admin/ratereview/reviewreport/<path:object_id>/history/` | ratereview_reviewreport_history | `history_view` |
| 145 | `admin/ratereview/reviewreport/<path:object_id>/delete/` | ratereview_reviewreport_delete | `delete_view` |
| 146 | `admin/ratereview/reviewreport/<path:object_id>/change/` | ratereview_reviewreport_change | `change_view` |
| 147 | `admin/ratereview/reviewreport/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 148 | `admin/wallet/platformfeeconfig/` | wallet_platformfeeconfig_changelist | `changelist_view` |
| 149 | `admin/wallet/platformfeeconfig/add/` | wallet_platformfeeconfig_add | `add_view` |
| 150 | `admin/wallet/platformfeeconfig/<path:object_id>/history/` | wallet_platformfeeconfig_history | `history_view` |
| 151 | `admin/wallet/platformfeeconfig/<path:object_id>/delete/` | wallet_platformfeeconfig_delete | `delete_view` |
| 152 | `admin/wallet/platformfeeconfig/<path:object_id>/change/` | wallet_platformfeeconfig_change | `change_view` |
| 153 | `admin/wallet/platformfeeconfig/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 154 | `admin/wallet/contractpaymentbreakdown/` | wallet_contractpaymentbreakdown_changelist | `changelist_view` |
| 155 | `admin/wallet/contractpaymentbreakdown/add/` | wallet_contractpaymentbreakdown_add | `add_view` |
| 156 | `admin/wallet/contractpaymentbreakdown/<path:object_id>/history/` | wallet_contractpaymentbreakdown_history | `history_view` |
| 157 | `admin/wallet/contractpaymentbreakdown/<path:object_id>/delete/` | wallet_contractpaymentbreakdown_delete | `delete_view` |
| 158 | `admin/wallet/contractpaymentbreakdown/<path:object_id>/change/` | wallet_contractpaymentbreakdown_change | `change_view` |
| 159 | `admin/wallet/contractpaymentbreakdown/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 160 | `admin/wallet/platformearning/` | wallet_platformearning_changelist | `changelist_view` |
| 161 | `admin/wallet/platformearning/add/` | wallet_platformearning_add | `add_view` |
| 162 | `admin/wallet/platformearning/<path:object_id>/history/` | wallet_platformearning_history | `history_view` |
| 163 | `admin/wallet/platformearning/<path:object_id>/delete/` | wallet_platformearning_delete | `delete_view` |
| 164 | `admin/wallet/platformearning/<path:object_id>/change/` | wallet_platformearning_change | `change_view` |
| 165 | `admin/wallet/platformearning/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 166 | `admin/wallet/paymentintent/` | wallet_paymentintent_changelist | `changelist_view` |
| 167 | `admin/wallet/paymentintent/add/` | wallet_paymentintent_add | `add_view` |
| 168 | `admin/wallet/paymentintent/<path:object_id>/history/` | wallet_paymentintent_history | `history_view` |
| 169 | `admin/wallet/paymentintent/<path:object_id>/delete/` | wallet_paymentintent_delete | `delete_view` |
| 170 | `admin/wallet/paymentintent/<path:object_id>/change/` | wallet_paymentintent_change | `change_view` |
| 171 | `admin/wallet/paymentintent/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 172 | `admin/wallet/withdrawalrequest/` | wallet_withdrawalrequest_changelist | `changelist_view` |
| 173 | `admin/wallet/withdrawalrequest/add/` | wallet_withdrawalrequest_add | `add_view` |
| 174 | `admin/wallet/withdrawalrequest/<path:object_id>/history/` | wallet_withdrawalrequest_history | `history_view` |
| 175 | `admin/wallet/withdrawalrequest/<path:object_id>/delete/` | wallet_withdrawalrequest_delete | `delete_view` |
| 176 | `admin/wallet/withdrawalrequest/<path:object_id>/change/` | wallet_withdrawalrequest_change | `change_view` |
| 177 | `admin/wallet/withdrawalrequest/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 178 | `admin/notification/notification/` | notification_notification_changelist | `changelist_view` |
| 179 | `admin/notification/notification/add/` | notification_notification_add | `add_view` |
| 180 | `admin/notification/notification/<path:object_id>/history/` | notification_notification_history | `history_view` |
| 181 | `admin/notification/notification/<path:object_id>/delete/` | notification_notification_delete | `delete_view` |
| 182 | `admin/notification/notification/<path:object_id>/change/` | notification_notification_change | `change_view` |
| 183 | `admin/notification/notification/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 184 | `admin/notification/activitylog/` | notification_activitylog_changelist | `changelist_view` |
| 185 | `admin/notification/activitylog/add/` | notification_activitylog_add | `add_view` |
| 186 | `admin/notification/activitylog/<path:object_id>/history/` | notification_activitylog_history | `history_view` |
| 187 | `admin/notification/activitylog/<path:object_id>/delete/` | notification_activitylog_delete | `delete_view` |
| 188 | `admin/notification/activitylog/<path:object_id>/change/` | notification_activitylog_change | `change_view` |
| 189 | `admin/notification/activitylog/<path:object_id>/` |  | `django.views.generic.base.RedirectView` |
| 190 | `admin/^(?P<app_label>auth|token_blacklist|accounts|wallet|category|contract|ratereview|notification)/$` | app_list | `app_index` |
| 191 | `admin/(?P<url>.*)$` |  | `catch_all_view` |
| 192 | `api/auth/login/` | auth_login | `accounts.views.LoginView` |
| 193 | `api/auth/refresh/` | auth_refresh | `accounts.views.RefreshTokenView` |
| 194 | `api/auth/logout/` | auth_logout | `accounts.views.LogoutView` |
| 195 | `api/auth/register/` | auth_register | `accounts.views.RegistrationView` |
| 196 | `api/auth/verify-email/` | verify_email | `accounts.views.VerifyEmailView` |
| 197 | `api/auth/resend-otp/` | resend_otp | `accounts.views.ResendOTPView` |
| 198 | `api/auth/password-reset/` | forgot_password | `accounts.views.ForgotPasswordView` |
| 199 | `api/auth/password-reset-confirm/` | reset_password_confirm | `accounts.views.ResetPasswordConfirmView` |
| 200 | `api/auth/technician/list/` | technician_list | `accounts.technician_views.TechnicianListView` |
| 201 | `api/auth/technician/profile/` | technician_profile | `accounts.technician_views.TechnicianProfileView` |
| 202 | `api/auth/technician/skills/` | technician_skills | `accounts.technician_views.TechnicianSkillsView` |
| 203 | `api/auth/technician/images/` | technician_images_list | `accounts.technician_views.TechnicianImagesListView` |
| 204 | `api/auth/technician/images/<uuid:image_id>/` | technician_image_detail | `accounts.technician_views.TechnicianImageDetailView` |
| 205 | `api/auth/technician/availability/` | technician_availability | `accounts.technician_views.TechnicianAvailabilityView` |
| 206 | `api/auth/technician/ratings/` | technician_ratings | `accounts.technician_views.TechnicianRatingsView` |
| 207 | `api/auth/client/profile/` | client_profile | `accounts.client_views.ClientProfileView` |
| 208 | `api/auth/profile/incomplete-fields/` | incomplete_fields | `accounts.client_views.IncompleteFieldsView` |
| 209 | `api/accounts/me/` | current_user | `accounts.views.CurrentUserView` |
| 210 | `api/categories/` | category-list | `category.views.CategoryViewSet` |
| 211 | `api/categories/<uuid:id>/` | category-detail | `category.views.CategoryViewSet` |
| 212 | `api/categories/^skills/$` | skill-list | `category.views.SkillViewSet` |
| 213 | `api/categories/^skills/(?P<pk>[^/.]+)/$` | skill-detail | `category.views.SkillViewSet` |
| 214 | `api/categories/^sub-skills/$` | subskill-list | `category.views.SubSkillViewSet` |
| 215 | `api/categories/^sub-skills/(?P<pk>[^/.]+)/$` | subskill-detail | `category.views.SubSkillViewSet` |
| 216 | `api/technicians/` | technician_list | `accounts.technician_views.TechnicianListView` |
| 217 | `api/technicians/me/` | technician_profile | `accounts.technician_views.TechnicianProfileView` |
| 218 | `api/technicians/me/skills/` | technician_skills | `accounts.technician_views.TechnicianSkillsView` |
| 219 | `api/technicians/me/images/` | technician_images_list | `accounts.technician_views.TechnicianImagesListView` |
| 220 | `api/technicians/me/images/<uuid:image_id>/` | technician_image_detail | `accounts.technician_views.TechnicianImageDetailView` |
| 221 | `api/technicians/me/availability/` | technician_availability | `accounts.technician_views.TechnicianAvailabilityView` |
| 222 | `api/technicians/me/ratings/` | technician_ratings | `accounts.technician_views.TechnicianRatingsView` |
| 223 | `api/technicians/<uuid:id>/` | technician_detail | `accounts.technician_views.TechnicianDetailView` |
| 224 | `api/clients/me/` | client_profile | `accounts.client_views.ClientProfileView` |
| 225 | `api/reviews/technician/<uuid:technician_id>/` | technician_reviews | `ratereview.views.TechnicianReviewsList` |
| 226 | `api/reviews/` | review_create | `ratereview.views.ReviewCreateView` |
| 227 | `api/reviews/<uuid:id>/` | review_detail_update | `ratereview.views.ReviewDetailUpdateView` |
| 228 | `api/reviews/<uuid:id>/respond/` | review_respond | `ratereview.views.ReviewTechnicianResponseView` |
| 229 | `api/reviews/<uuid:id>/helpful/` | review_helpful | `ratereview.views.ReviewHelpfulView` |
| 230 | `api/reviews/<uuid:id>/report/` | review_report | `ratereview.views.ReviewReportView` |
| 231 | `api/reviews/<uuid:id>/moderate/publish/` | review_moderate_publish | `ratereview.views.ReviewModeratePublishView` |
| 232 | `api/reviews/<uuid:id>/moderate/hide/` | review_moderate_hide | `ratereview.views.ReviewModerateHideView` |
| 233 | `api/reviews/<uuid:id>/moderate/verify/` | review_moderate_verify | `ratereview.views.ReviewModerateVerifyView` |
| 234 | `api/reviews/<uuid:id>/moderate/unverify/` | review_moderate_unverify | `ratereview.views.ReviewModerateUnverifyView` |
| 235 | `api/contracts/` | contract-list | `contract.views.ContractListCreateView` |
| 236 | `api/contracts/<uuid:contract_id>/` | contract-detail | `contract.views.ContractDetailView` |
| 237 | `api/contracts/<uuid:contract_id>/accept/` | contract-accept | `contract.views.ContractAcceptView` |
| 238 | `api/contracts/<uuid:contract_id>/cancel/` | contract-cancel | `contract.views.ContractCancelView` |
| 239 | `api/contracts/<uuid:contract_id>/stages/` | contract-stage-list | `contract.views.ContractStageListView` |
| 240 | `api/contracts/<uuid:contract_id>/stages/<uuid:stage_id>/` | contract-stage-detail | `contract.views.ContractStageDetailView` |
| 241 | `api/contracts/<uuid:contract_id>/stages/<uuid:stage_id>/submit/` | contract-stage-submit | `contract.views.ContractStageSubmitView` |
| 242 | `api/contracts/<uuid:contract_id>/stages/<uuid:stage_id>/approve/` | contract-stage-approve | `contract.views.ContractStageApproveView` |
| 243 | `api/contracts/<uuid:contract_id>/extension-requests/` | contract-extension-list | `contract.views.ContractExtensionListView` |
| 244 | `api/contracts/<uuid:contract_id>/extension-requests/create/` | contract-extension-create | `contract.views.ContractExtensionCreateView` |
| 245 | `api/contracts/<uuid:contract_id>/extension-requests/<uuid:request_id>/approve/` | contract-extension-approve | `contract.views.ContractExtensionRespondView` |
| 246 | `api/contracts/<uuid:contract_id>/extension-requests/<uuid:request_id>/reject/` | contract-extension-reject | `contract.views.ContractExtensionRespondView` |
| 247 | `api/wallet/me/` | wallet-me | `wallet.views.WalletMeView` |
| 248 | `api/wallet/transactions/` | wallet-transactions | `wallet.views.WalletTransactionListView` |
| 249 | `api/wallet/withdrawals/` | withdrawal-list | `wallet.views.WithdrawalListCreateView` |
| 250 | `api/wallet/withdrawals/<uuid:withdrawal_id>/` | withdrawal-detail | `wallet.views.WithdrawalDetailView` |
| 251 | `api/wallet/withdrawals/<uuid:withdrawal_id>/approve/` | withdrawal-approve | `wallet.views.WithdrawalApproveView` |
| 252 | `api/wallet/withdrawals/<uuid:withdrawal_id>/reject/` | withdrawal-reject | `wallet.views.WithdrawalRejectView` |
| 253 | `api/wallet/payment-intents/` | payment-intent-list | `wallet.views.PaymentIntentListView` |
| 254 | `api/wallet/payment-intents/<uuid:intent_id>/` | payment-intent-detail | `wallet.views.PaymentIntentDetailView` |
| 255 | `api/wallet/payment-intents/<uuid:intent_id>/mark-paid/` | payment-intent-mark-paid | `wallet.views.PaymentIntentMarkPaidView` |
| 256 | `api/wallet/fee-config/` | fee-config-list | `wallet.views.FeeConfigListView` |
| 257 | `api/wallet/contracts/<uuid:contract_id>/breakdown/` | contract-breakdown | `wallet.views.ContractBreakdownView` |
| 258 | `api/notifications/` | notification_list | `notification.views.NotificationListView` |
| 259 | `api/notifications/unread-count/` | notification_unread_count | `notification.views.NotificationUnreadCountView` |
| 260 | `api/notifications/<uuid:id>/` | notification_detail | `notification.views.NotificationDetailView` |
| 261 | `api/notifications/<uuid:id>/mark-read/` | notification_mark_read | `notification.views.NotificationMarkReadView` |
| 262 | `api/notifications/<uuid:id>/mark-unread/` | notification_mark_unread | `notification.views.NotificationMarkUnreadView` |
| 263 | `api/notifications/mark-all-read/` | notification_mark_all_read | `notification.views.NotificationMarkAllReadView` |
| 264 | `api/notifications/activity/` | activity_log_list | `notification.views.ActivityLogListView` |
| 265 | `api/admin/dashboard/summary/` | admin_dashboard_summary | `dashboard.views.DashboardSummaryView` |
| 266 | `api/admin/users/` | admin_user_list | `dashboard.views.AdminUserListView` |
| 267 | `api/admin/users/<uuid:id>/` | admin_user_detail_update | `dashboard.views.AdminUserDetailUpdateView` |
| 268 | `api/admin/users/<uuid:id>/activate/` | admin_user_activate | `dashboard.views.AdminUserActivateView` |
| 269 | `api/admin/users/<uuid:id>/deactivate/` | admin_user_deactivate | `dashboard.views.AdminUserDeactivateView` |
| 270 | `api/admin/technicians/` | admin_technician_list | `dashboard.views.AdminTechnicianListView` |
| 271 | `api/admin/technicians/pending/` | admin_technician_pending | `dashboard.views.AdminTechnicianPendingView` |
| 272 | `api/admin/technicians/<uuid:id>/` | admin_technician_detail | `dashboard.views.AdminTechnicianDetailView` |
| 273 | `api/admin/technicians/<uuid:id>/approve/` | admin_technician_approve | `dashboard.views.AdminTechnicianApproveView` |
| 274 | `api/admin/technicians/<uuid:id>/reject/` | admin_technician_reject | `dashboard.views.AdminTechnicianRejectView` |
| 275 | `api/admin/contracts/` | admin_contract_list | `dashboard.views.AdminContractListView` |
| 276 | `api/admin/contracts/<uuid:id>/` | admin_contract_detail | `dashboard.views.AdminContractDetailView` |
| 277 | `api/admin/contracts/<uuid:id>/force-cancel/` | admin_contract_force_cancel | `dashboard.views.AdminContractForceCancelView` |
| 278 | `api/admin/reviews/` | admin_review_list | `dashboard.views.AdminReviewListView` |
| 279 | `api/admin/reviews/flagged/` | admin_review_flagged | `dashboard.views.AdminReviewFlaggedView` |
| 280 | `api/admin/reviews/<uuid:id>/` | admin_review_detail | `dashboard.views.AdminReviewDetailView` |
| 281 | `api/admin/reviews/<uuid:id>/hide/` | admin_review_hide | `dashboard.views.AdminReviewHideView` |
| 282 | `api/admin/reviews/<uuid:id>/publish/` | admin_review_publish | `dashboard.views.AdminReviewPublishView` |
| 283 | `api/admin/reviews/<uuid:id>/verify/` | admin_review_verify | `dashboard.views.AdminReviewVerifyView` |
| 284 | `api/admin/reviews/<uuid:id>/unverify/` | admin_review_unverify | `dashboard.views.AdminReviewUnverifyView` |
| 285 | `api/admin/finance/summary/` | admin_finance_summary | `dashboard.views.AdminFinanceSummaryView` |
| 286 | `api/admin/finance/platform-earnings/` | admin_finance_earnings | `dashboard.views.AdminPlatformEarningListView` |
| 287 | `api/admin/finance/payment-intents/` | admin_finance_payment_intents | `dashboard.views.AdminPaymentIntentListView` |
| 288 | `api/admin/finance/payment-intents/<uuid:id>/mark-paid/` | admin_finance_pi_mark_paid | `dashboard.views.AdminPaymentIntentMarkPaidView` |
| 289 | `api/admin/finance/withdrawals/` | admin_finance_withdrawals | `dashboard.views.AdminWithdrawalListView` |
| 290 | `api/admin/finance/withdrawals/<uuid:id>/approve/` | admin_finance_withdrawal_approve | `dashboard.views.AdminWithdrawalApproveView` |
| 291 | `api/admin/finance/withdrawals/<uuid:id>/reject/` | admin_finance_withdrawal_reject | `dashboard.views.AdminWithdrawalRejectView` |
| 292 | `api/admin/activity/` | admin_activity_list | `dashboard.views.AdminActivityListView` |
| 293 | `api/health/` |  | `health` |
| 294 | `^media/(?P<path>.*)$` |  | `serve` |
| 295 | `^static/(?P<path>.*)$` |  | `serve` |
| 296 | `^media/(?P<path>.*)$` |  | `serve` |
| 297 | `^static/(?P<path>.*)$` |  | `serve` |
