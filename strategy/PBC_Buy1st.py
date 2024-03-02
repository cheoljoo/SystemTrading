from api.Kiwoom import *
from util.make_up_universe import *
from util.db_helper import *
from util.time_helper import *
from util.notifier import *
import math
import traceback

  
class PBC_Buy1st (QThread):
    def __init__(self):
        QThread.__init__(self)
        self.strategy_name = "PBC_Buy1st"
        self.kiwoom = Kiwoom()

        # 주문할 ticker를 담을 딕셔너리
        self.target_items = {
            '종목코드' : "005930",
            'is시가Down'    : False,   #시가 아래로 내려가면 True
            'is시가UpAgain' : False,   #시가 아래로 갔다 올라오면 True
            '감시시작' : 0,     # 0 감시시작x 1 시작 
            '매수여부' : 0,     # 0 매수안함, 1 매수
            '매도여부' : 0,     # 0 매도안함, 1 매도
            }
        self.target_data = {
            "0005930" : (False, False, False, False, False)
        }
        # 계좌 예수금
        self.deposit = 0

        # 초기화 함수 성공 여부 확인 변수
        self.is_init_success = False
        self.stock_account = ""

        self.init_strategy()


    def init_strategy(self):
        """전략 초기화 기능을 수행하는 함수"""
        try:

            # 감시 종목 조회, 없으면 생성
            self.check_and_get_target_items()
            
            #df = self.kiwoom.get_price_data("005930")
            #print(df)

            # Kiwoom > 주문정보 확인
            self.kiwoom.get_order()

            # Kiwoom > 잔고 확인
            self.kiwoom.get_balance()
            # Kiwoom > 예수금 확인
            self.deposit = self.kiwoom.get_deposit()

            # 주식계좌
            accounts = self.kiwoom.GetLoginInfo("ACCNO")

            #self.text_edit.append("계좌번호 :" + accounts.rstrip(';'))

            self.stock_account = accounts.rstrip(';')

            print (accounts)
            send_message_bot(self.stock_account,0)
            send_message_bot(self.deposit,0)
            self.is_init_success = True

        except Exception as e:
            print(traceback.format_exc())
            # LINE 메시지를 보내는 부분
            send_message_bot(traceback.format_exc(), 0)

    def check_and_get_target_items(self):
        """관심종목 존재하는지 확인하고 없으면 생성하는 함수"""
        fids = get_fid("체결시간")
        codes = self.target_items['종목코드']
        self.kiwoom.set_real_reg("9999", codes, fids, "0")
       
    def run(self):
        """실질적 수행 역할을 하는 함수"""
        while self.is_init_success:
            try:
                # (0)장중인지 확인
                if not check_transaction_open():
                    print("장시간이 아니므로 5분간 대기합니다.")
                    # time.sleep(1 * 60)
                    # continue

                for code in self.target_items:
                    print (code)

                    # (1)접수한 주문이 있는지 확인
                    if code in self.kiwoom.order.keys():
                        # (2)주문이 있음
                        print('접수 주문', self.kiwoom.order[code])

                        # (2.1) '미체결수량' 확인하여 미체결 종목인지 확인
                        if self.kiwoom.order[code]['미체결수량'] > 0:
                            pass
                    # (3)보유 종목인지 확인
                    elif code in self.kiwoom.balance.keys():
                        print('보유 종목', self.kiwoom.balance[code])
                        # (6)매도 대상 확인
                        if self.check_sell_signal(code):
                            # (7)매도 대상이면 매도 주문 접수
                            self.order_sell(code)

                    else:
                        # (4)접수 주문 및 보유 종목이 아니라면 매수대상인지 확인 후 주문접수
                        self.check_buy_signal_and_order(code)
                        #print ("444")

                    time.sleep(0.3)
            except Exception as e:
                print(traceback.format_exc())
                # telegram 메시지를 보내는 부분
                send_message_bot(traceback.format_exc(), 0)

    def check_sell_signal(self, code):
        """매도대상인지 확인하는 함수"""
        universe_item = self.universe[code]

        # (1)현재 체결정보가 존재하지 않는지 확인
        if code not in self.kiwoom.universe_realtime_transaction_info.keys():
            # 체결 정보가 없으면 더 이상 진행하지 않고 함수 종료
            print("매도대상 확인 과정에서 아직 체결정보가 없습니다.")
            return
        
        # (2)실시간 체결 정보가 존재하면 현시점의 시가 / 고가 / 저가 / 현재가 / 누적 거래량이 저장되어 있음
        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']

        # 오늘 가격 데이터를 과거 가격 데이터(DataFrame)의 행으로 추가하기 위해 리스트로 만듦
        today_price_data = [open, high, low, close, volume]
        #print (today_price_data)

        # 다시 시가 아래로 내려가면 매도 (손절)
        if close < open: 
            return True
        
        #수익보고 익절 해야 함. (익절)
        if close > (open + ((open * 2) / 100)):
            return True

        return False

    def order_sell(self, code):
        """매도 주문 접수 함수"""
        # 보유 수량 확인(전량 매도 방식으로 보유한 수량을 모두 매도함)
        quantity = self.kiwoom.balance[code]['보유수량']

        # 최우선 매도 호가 확인
        ask = self.kiwoom.universe_realtime_transaction_info[code]['(최우선)매도호가']

        order_result = self.kiwoom.send_order('send_sell_order', '1001', 2, code, quantity, ask, '00')

        # LINE 메시지를 보내는 부분
        message = "[{}]sell order is done! quantity:{}, ask:{}, order_result:{}".format(code, quantity, ask,
                                                                                        order_result)
        send_message_bot(message, 0)

    def check_buy_signal_and_order(self, code):
        """매수 대상인지 확인하고 주문을 접수하는 함수"""

        # 매수 가능 시간 확인
       # if not check_adjacent_transaction_closed():
        #    return False
        
        # (1)현재 체결정보가 존재하지 않는지 확인
        if code not in self.kiwoom.universe_realtime_transaction_info.keys():
            # 존재하지 않다면 더이상 진행하지 않고 함수 종료
            print("매수대상 확인 과정에서 아직 체결정보가 없습니다.")
            return
        
        # (2)실시간 체결 정보가 존재하면 현 시점의 시가 / 고가 / 저가 / 현재가 / 누적 거래량이 저장되어 있음
        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']

        # 오늘 가격 데이터를 과거 가격 데이터(DataFrame)의 행으로 추가하기 위해 리스트로 만듦
        today_price_data = [open, high, low, close, volume]

        """ 매수조건
        1. 현재가가 시가 아래로 내렸갔다 올라와야 한다. 
        """

        if close < open:
            # 시가 아래로 내려 갔다.
            if self.target_items['is시가Down'] is not True:
                self.target_items['is시가Down'] = True
            pass    

        if close >= open:   #현재가가 시가보다 크거나 같으면.. (상승)
            if self.target_items['is시가Down'] is True:
                # 다시 올라오면 매수. 
                # 주문 수량
                quantity = 10 
                bid = close

                # (9)계산을 바탕으로 지정가(00), 시장가(03) 매수 주문 접수
                order_result = self.kiwoom.send_order('send_buy_order', '1001', 1, code, quantity, bid, '03')
                print(order_result)

                # _on_chejan_slot가 늦게 동작할 수도 있기 때문에 미리 약간의 정보를 넣어둠
                self.kiwoom.order[code] = {'주문구분': '매수', '미체결수량': quantity}

                # Telegram 메시지를 보내는 부분
                message = "[{}]buy order is done! quantity:{}, bid:{}, order_result:{}, deposit:{}, get_balance_count:{}, get_buy_order_count:{}, balance_len:{}".format(
                    code, quantity, bid, order_result, self.deposit, self.get_balance_count(), self.get_buy_order_count(),
                    len(self.kiwoom.balance))
                send_message_bot(message, 0)
            else:
                print ("시가 아래로 내려온적이 없음")        
    
    def get_balance_count(self):
        """매도 주문이 접수되지 않은 보유 종목 수를 계산하는 함수"""
        balance_count = len(self.kiwoom.balance)
        # kiwoom balance에 존재하는 종목이 매도 주문 접수되었다면 보유 종목에서 제외시킴
        for code in self.kiwoom.order.keys():
            if code in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == "매도" and self.kiwoom.order[code]['미체결수량'] == 0:
                balance_count = balance_count - 1
        return balance_count

    def get_buy_order_count(self):
        """매수 주문 종목 수를 계산하는 함수"""
        buy_order_count = 0
        # 아직 체결이 완료되지 않은 매수 주문
        for code in self.kiwoom.order.keys():
            if code not in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == "매수":
                buy_order_count = buy_order_count + 1
        return buy_order_count
