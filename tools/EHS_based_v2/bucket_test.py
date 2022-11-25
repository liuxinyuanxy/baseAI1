import tools.EHS_based_v2.EHS_based_bucket as EHS_based_bucket

#lossy()函数为flop，turn，river阶段使用的抽象方法，输入为公共牌和手牌，输出为1-200之间的一个整数值
#函数接收手牌的形式为list，手牌只有两张，公共牌有3-5张
lossy_bucket = EHS_based_bucket.lossy(["As", "Ad", "Jd", "4d", "5d"], ["Ac", "Ah"])
print(lossy_bucket)


#单线程的有损抽象
lossy_bucket_single = EHS_based_bucket.lossy_single(["As", "Ad", "Jd", "4d", "5d"], ["Ac", "Ah"])
print(lossy_bucket_single)




#lossless()函数为pre-flop阶段使用的抽象方法，为无损抽象，输入仅为手牌，输出为1-169之间的一个整数值
#函数接收手牌的形式为list，手牌只有两张
lossless_bucket = EHS_based_bucket.lossless(["Ks", "Ac"])
print(lossless_bucket)


