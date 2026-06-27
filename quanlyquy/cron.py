from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from .models import InvestmentProposal, ProposalVote, Transaction

def auto_process_voting_cron():
    now = timezone.now()
    
    # Quét DB tìm các đề xuất đang biểu quyết nhưng đã quá hạn 3 ngày
    expired_proposals = InvestmentProposal.objects.filter(status='PENDING', expired_at__lte=now)
    
    for proposal in expired_proposals:
        fund = proposal.fund
        
        # Đếm tổng thành viên thực tế của quỹ lớp (ví dụ lấy toàn bộ Active User trong hệ thống)
        total_members = User.objects.filter(is_active=True).count()
        if total_members == 0: continue
        
        with transaction.atomic():
            # 1. Tìm những thành viên chưa chịu bấm biểu quyết trên giao diện Web
            voted_user_ids = ProposalVote.objects.filter(proposal=proposal).values_list('user_id', flat=True)
            all_users = User.objects.filter(is_active=True)
            
            # 2. Tự động chuyển những ai "im lặng" thành ĐỒNG Ý (AUTO_YES)
            for user in all_users:
                if user.id not in voted_user_ids:
                    ProposalVote.objects.create(
                        proposal=proposal,
                        user=user,
                        choice='AUTO_YES',
                        voted_at=now
                    )
            
            # 3. Tính tỷ lệ phiếu bầu
            total_yes_votes = ProposalVote.objects.filter(proposal=proposal, choice__in=['VOTE_YES', 'AUTO_YES']).count()
            yes_percentage = (total_yes_votes / total_members) * 100
            
            # 4. Nếu >= 70% thì duyệt đề xuất và thực hiện giải ngân tài sản
            if yes_percentage >= 70.0:
                proposal.status = 'APPROVED'
                
                # Trừ tiền mặt khả dụng, chuyển sang danh mục tài sản đầu tư (Giai đoạn 3)
                if fund.total_cash >= proposal.amount:
                    fund.total_cash -= proposal.amount
                    fund.total_invest += proposal.amount
                    fund.save()
                    
                    # Ghi nhận lịch sử giao dịch Xuất Quỹ
                    Transaction.objects.create(
                        fund=fund,
                        amount=proposal.amount,
                        type='CHI',
                        status='SUCCESS',
                        order_id=f"INVEST_{proposal.id}_{int(now.timestamp())}"
                    )
            else:
                proposal.status = 'REJECTED'
                
            proposal.save()