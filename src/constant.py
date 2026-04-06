from src.tickets.schemas import IssueType

collection_urls = [
    # 1. Onboarding and Sign up (12 articles)
    "https://help.raenest.com/en/collections/3533693-onboarding-and-sign-up",
    # 2. US Bank Account for US Residents (2 articles)
    "https://help.raenest.com/en/collections/15733141-us-bank-account-for-us-residents",
    # 3. Bank Accounts (9 articles)
    "https://help.raenest.com/en/collections/3486985-bank-accounts",
    # 4. Employment Details (23 articles)
    "https://help.raenest.com/en/collections/15831197-employment-details",
    # 5. Invoicing and Employer Billing (1 article)
    "https://help.raenest.com/en/collections/3533698-invoicing-and-employer-billing",
    # 6. Raenest Fast Track (2 articles)
    "https://help.raenest.com/en/collections/16579670-raenest-fast-track",
    # 7. Transfer and Withdraw Fund (2 articles)
    "https://help.raenest.com/en/collections/3533863-transfer-and-withdraw-fund",
    # 8. Virtual cards (9 articles)
    "https://help.raenest.com/en/collections/3553353-virtual-cards",
    # 9. Wallets & Currencies (4 articles)
    "https://help.raenest.com/en/collections/5556772-wallets-currencies",
    # 10. Funding Your Wallet (2 articles)
    "https://help.raenest.com/en/collections/5556685-funding-your-wallet",
    # 11. Securing your Account (3 articles)
    "https://help.raenest.com/en/collections/3533702-securing-your-account",
    # 12. Fees and Charges (3 articles)
    "https://help.raenest.com/en/collections/3533699-fees-and-charges",
    # 13. Bill Payments (1 article)
    "https://help.raenest.com/en/collections/13716686-bill-payments",
    # 14. Raenest Perks (2 articles)
    "https://help.raenest.com/en/collections/14162840-raenest-perks",
    # 15. Add Money (3 articles)
    "https://help.raenest.com/en/collections/15731858-add-money",
    # 16. Stablecoins on Raenest (1 article)
    "https://help.raenest.com/en/collections/15732358-stablecoins-on-raenest",
    # 17. Payment Links (1 article)
    "https://help.raenest.com/en/collections/15877261-payment-links",
    # 18. U.S. Stocks (3 articles)
    "https://help.raenest.com/en/collections/15732786-u-s-stocks",
]

ISSUE_TYPE_TO_DOC_TYPES = {
    IssueType.account_verification: ["us_bank_account_for_us_residents"],
    IssueType.cards: ["virtual_cards"],
    IssueType.transfers: [
        "transfer_and_withdraw_fund",
        "bank_accounts",
        "wallets_currencies",
    ],
    IssueType.integrations: ["employment_details", "raenest_fast_track"],
    IssueType.fees: ["fees_and_charges"],
    IssueType.account_access: [
        "securing_your_account",
        "add_money",
    ],  # may also include KYC limits
    IssueType.technical: [
        "playstore_review",
        "virtual_cards",
    ],  # app issues + card failure reasons
    IssueType.general: None,  # no filter – search everything
}
