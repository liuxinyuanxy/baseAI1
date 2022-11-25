import tools.EHS_based_v2.parallel_holdem_calc_dev as parallel_holdem_calc_dev
import tools.EHS_based_v2.holdem_calc as holdem_calc
import os
curPath = os.path.abspath(os.path.dirname(__file__))
def lossy(board_card, hole_card):

    hole_card.extend(["?","?"]) #unknown opponent hands 
    L = parallel_holdem_calc_dev.calculate(board_card, False, 1000, None, hole_card, False)
    EHS = L[0]/2 + L[1] - L[2]

    classify = False
    a = 0
    b = 0
    while classify == False:
        if EHS <= a:
            classify = True
        else:
            a += 0.005
            b += 1
    return b  


def lossy_single(board_card, hole_card):

    hole_card.extend(["?","?"]) #unknown opponent hands 
    L = holdem_calc.calculate(board_card, False, 1000, None, hole_card, False)
    EHS = L[0]/2 + L[1] - L[2]

    classify = False
    a = 0
    b = 0
    while classify == False:
        if EHS <= a:
            classify = True
        else:
            a += 0.005
            b += 1
    return b  



def lossless(hole_card):
    dict = {"2": 2, "3": 3, "4": 4,"5": 5, 
            "6": 6,"7": 7, "8": 8, "9": 9,
             "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    card1 = hole_card[0]
    card2 = hole_card[1]
    # print(card1,card2)
    rank1_value = dict[card1[:1]]
    rank2_value = dict[card2[:1]]
    suit1 = card1[1:2]
    suit2 = card2[1:2]
    if rank1_value == rank2_value:
        suit1 = "h"
        suit2 = "s"
        rank1 = list(dict.keys())[list(dict.values()).index(rank1_value)]
        rank2 = list(dict.keys())[list(dict.values()).index(rank2_value)]
        card1 = rank1 + suit1
        card2 = rank2 + suit2
    else:
        if suit1 == suit2:
            if rank1_value < rank2_value:
                pass
            else:
                temp = rank1_value
                rank1_value = rank2_value
                rank2_value = temp
            suit1 = "h"
            suit2 = "h"
            rank1 = list(dict.keys())[list(dict.values()).index(rank1_value)]
            rank2 = list(dict.keys())[list(dict.values()).index(rank2_value)]
        else:
            if rank1_value > rank2_value:
                pass
            else:
                temp = rank1_value
                rank1_value = rank2_value
                rank2_value = temp
            suit1 = "h"
            suit2 = "s"
            rank1 = list(dict.keys())[list(dict.values()).index(rank1_value)]
            rank2 = list(dict.keys())[list(dict.values()).index(rank2_value)]
        card1 = rank1 + suit1
        card2 = rank2 + suit2
    space = " "
    hole_card_find = card1 + space + card2
    # print(hole_card_find)
    
    poker_line=0;
    f = open(curPath+'/preflop_canonical_hands.txt','r',encoding='utf8')
    
    for lines in f.readlines():
        poker_line=poker_line+1;
        if lines.find(hole_card_find)!=-1:
           break 

    f.close()
    return poker_line

  