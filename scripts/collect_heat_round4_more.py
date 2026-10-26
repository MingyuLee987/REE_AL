import collect_heat_round4_extra as m
m.ROUND=m.ROOT/'outputs/heat_expansion_round4_more_20261023'
m.CANDIDATE_FILE='round4_more_candidates.csv'
m.SPECS=[
 ('10.3390/ma15010024','Effect of Annealing on Microstructure and Corrosion Behavior of Interstitial Free Steel','materials',15,24),
]
m.DIRECT=[
 ('10.17222/mit.2021.014','Corrosion behaviour of tempered 42CrMo4 steel','https://www.dlib.si/stream/URN%3ANBN%3ASI%3ADOC-0B6IHKC9/baba7c8f-f38a-4f84-9d84-a1179733d18f/PDF'),
 ('10.24425/amm.2019.131106','Corrosion Resistance of the Nanostructured X37CRMOV5-1 Steel','https://journals.pan.pl/Content/114513/PDF/AMM-2020-1-16-Skolek.pdf?handler=pdf'),
]
m.ADDITIONAL=[
 ('10.1002/adem.202401442','Determining the Necessity of Post-Processing Heat Treatment for the 316L Stainless Steel Manufactured by Laser Powder Bed Fusion through Evaluation of Mechanical and Corrosion Properties'),
 ('10.1002/maco.202112775','Influence of reversed austenite on the properties of a 13Cr4NiMo ultra-low carbon martensitic stainless steel in different environments'),
 ('10.1155/2013/587514','Influence of Heat Treatment on the Corrosion of Microalloyed Steel in Sodium Chloride Solution'),
 ('10.1155/2018/7638274','Effects of Alloying Elements (Cr, Mn) on Corrosion Properties of the High-Strength Steel in 3.5% NaCl Solution'),
]
if __name__=='__main__':m.main()
