#!/usr/bin/env python3
"""
write_evidence_27.py — Step 2 batch evidence extraction for 27 abstract-only papers.

LLM-driven extraction completed manually (the model itself); this script just
writes the structured rows into evidence_table.csv with proper CSV escaping.

Usage:
  python3 write_evidence_27.py [output_path]

  output_path: Optional. Path to output CSV file. Defaults to 'evidence_table.csv' in current directory.

Example:
  python3 write_evidence_27.py $RUN_DIR/reading/evidence_table.csv
"""
import csv
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence_table.csv")

HEADER = ['paper_uid', 'study_type', 'population', 'intervention', 'outcome', 'comparator',
         'method', 'key_finding_1', 'key_finding_2', 'key_finding_3',
         'extraction_confidence', 'fulltext_required', 'extraction_source']

ROWS = [
    # 1. P-05 (dryrun reused)
    ['doi:10.1016/j.apenergy.2023.122090', 'empirical_optimization',
     'EV battery (BTMS controlled)', 'Multi-objective optimal control of cooling+heating',
     'Degradation rate ↓ + energy use ↓ (with thermal safety)',
     'Multiple driving cycles + ambient temps',
     'Multi-objective optimization + dynamic programming + simulation',
     'Strategy reduces degradation and energy simultaneously',
     'Validated across driving cycles + ambient temps', '',
     'high', 'medium', 'abstract+keywords'],

    # 2. PCM + HP hybrid
    ['doi:10.1016/j.applthermaleng.2021.116665', 'empirical_pcm',
     'EV battery pack with PCM + heat pipe',
     'PCM + heat pipe hybrid BTMS with optimized PCM thickness distribution',
     'Max temp difference ↓30% via PCM thickness optimization',
     'HP-only BTMS',
     'Numerical simulation + parameter sweep (h; latent heat; PCM thickness)',
     'PCM reduces battery pack temp difference vs HP-only',
     'Higher h / latent heat / PCM thickness reduces max temp; melting < HP start temp causes large ΔT',
     'Optimized PCM thickness distribution reduces max ΔT by 30%',
     'high', 'medium', 'abstract+keywords'],

    # 3. Air cooling with spoilers
    ['doi:10.1016/j.applthermaleng.2021.116932', 'empirical_cfd',
     'EV battery module (Z-shaped air cooling BTMS)',
     'Spoilers in battery gap spacing',
     'plan 1 (16 long straight spoilers) MaxT ↓3.52K vs no-spoiler; after MOGA opt MaxT 307.58K (↓2.24K) + volume ↓4.87%',
     'Initial plan without spoilers',
     'CFD + Latin hypercube sampling + genetic programming surrogate + MOGA',
     '16 long straight spoilers reduce MaxT by 3.52K vs no-spoiler baseline',
     'MOGA optimization further reduces MaxT 2.24K + volume 4.87%',
     'GP surrogate enables efficient multi-objective optimization',
     'high', 'medium', 'abstract+keywords'],

    # 4. Multiscale encapsulated inorganic PCM
    ['doi:10.1016/j.applthermaleng.2021.117002', 'empirical_material',
     '20-cell Li-ion battery pack',
     'Multiscale encapsulated inorganic PCM (SAT-Urea + EG + organosilicon sealant)',
     'Thermal conductivity 4.96 W/(m·K); fire-resistant; cooler + more uniform vs organic PCM',
     'Organic PCM',
     'Multiscale encapsulation + thermal/fire test',
     'Multiscale encapsulation reaches k=4.96 W/(m·K) and prevents leakage',
     'Inorganic PCM is non-flammable hence safer than organic',
     'Cooler + more uniform thermal env in 20-cell pack vs organic PCM',
     'high', 'medium', 'abstract+keywords'],

    # 5. P-02 (dryrun reused)
    ['doi:10.1016/j.applthermaleng.2021.117242', 'empirical_cfd',
     'EV battery pack', 'Z-type air-cooled BTMS + parallel plate',
     'Tmax ↓3.42K(6.26%); ΔT ↓6.4K(90.78%)',
     'Standard Z-type vs improved + 9 prototypes',
     'CFD simulation + 9 prototypes',
     'Number of parallel plates is key variable',
     'Optimization yields ~90% ΔT reduction',
     '4 plate schemes effective on 9 prototypes',
     'high', 'medium', 'abstract+keywords'],

    # 6. Liquid-cooling BTMS review
    ['doi:10.1016/j.applthermaleng.2022.119626', 'review',
     'EV liquid-cooling BTMS',
     'Various design improvements (channel/jacket/cold plate/coolant/refrigeration/HP/hybrid)',
     'Cooling performance gaps + future directions for EV industry',
     'Among 7 improvement approaches',
     'Comprehensive literature review',
     'Liquid-cooling has higher heat transfer efficiency than passive/active air-cooling',
     'Cooling channel + refrigerant cooling + liquid-PCM hybrid are most effective improvements',
     'Research gaps highlighted for EV industry',
     'medium', 'medium', 'abstract+keywords'],

    # 7. Fast-charging BTMS review
    ['doi:10.1016/j.applthermaleng.2023.120303', 'review',
     'EV BTMS for fast-charging',
     'BTMS technologies (air/liquid/PCM/HP/hybrid)',
     'State-of-the-art advances + challenges (qualitative)',
     'Among various cooling techniques',
     'State-of-the-art review',
     'Fast-charging is key bottleneck for EV adoption due to thermal management',
     'Hybrid cooling systems gain attention for fast-charging',
     '',
     'medium', 'medium', 'abstract+keywords'],

    # 8. Air-cooled with control strategy
    ['doi:10.1016/j.applthermaleng.2023.121578', 'empirical_optimization',
     'EV battery pack air-cooled BTMS',
     'Air-cooled BTMS with control strategy',
     'Cooling performance ↑ + energy consumption ↓ (qualitative)',
     'Without control strategy',
     'Experimental + numerical investigation',
     'Control strategy improves cooling performance and reduces energy use',
     'Effects of airflow rate and ambient temp studied',
     '',
     'medium', 'medium', 'abstract+keywords'],

    # 9. Flexible CPCM
    ['doi:10.1016/j.cej.2021.131116', 'empirical_material',
     'Li-ion battery pack',
     'Flexible composite PCM (room-temperature flexibility)',
     'Reduced max temp + temp difference (qualitative); good flexibility + high k + excellent BTM performance',
     '',
     'Material development + thermal/mechanical/BTM property test',
     'Flexible CPCM minimizes thermal contact resistance in BTMS',
     'Good flexibility + high thermal conductivity',
     'Effective for max temp + temp difference reduction',
     'medium', 'medium', 'abstract+keywords'],

    # 10. PCM safety review
    ['doi:10.1016/j.ensm.2022.09.007', 'review',
     'PCM-based BTM systems',
     'Safety strategies (design opt + material selection + system integration)',
     'Hazard identification + mitigation strategies',
     'Various PCMs thermal stability',
     'Literature review + thermal stability evaluation',
     'PCM thermal stability is critical safety issue',
     'System hazards span thermal management design + material selection + integration',
     'Strategies for hazard mitigation proposed',
     'medium', 'medium', 'abstract+keywords'],

    # 11. Passive PCM BTMS
    ['doi:10.1016/j.est.2021.102279', 'empirical_pcm',
     'Pouch lithium-ion battery cells',
     'Passive low-cost PCM unit BTMS',
     'Reduced max temp + max temp difference at end of discharge; temperature retaining via insulation',
     '',
     'Numerical heat transfer model + parametric study',
     'PCM units effectively decrease max temp + max temp difference',
     'Insulating heat dissipation provides temperature retaining function',
     'Design parameters (k; viscosity; latent heat; thickness; shell k) significantly affect performance',
     'high', 'medium', 'abstract+keywords'],

    # 12. Liquid-immersed BTMS
    ['doi:10.1016/j.est.2021.103835', 'empirical_immersion',
     'Lithium-ion pouch battery pack',
     'Liquid-immersed BTMS',
     'Reduced max temp + temp difference (qualitative)',
     '',
     'Experimental + numerical investigation',
     'Liquid-immersed BTMS effectively reduces max temp + temp difference',
     'Flow rate; immersion liquid; battery arrangement affect performance',
     '',
     'medium', 'medium', 'abstract+keywords'],

    # 13. Nanofluids review
    ['doi:10.1016/j.est.2022.104385', 'review',
     'EV Li-ion batteries',
     'Nanofluid-based BTMS',
     'Heat transfer enhancement + applicability review (qualitative)',
     'Various BTMSs and nanofluid types',
     'Literature review',
     'Nanofluids enhance heat transfer in BTMSs',
     'Multiple application domains in BTMSs reviewed',
     '',
     'low', 'medium', 'abstract+keywords'],

    # 14. BTM safety review
    ['doi:10.1016/j.ijft.2022.100171', 'review',
     'Li-ion BTM systems',
     'BTM technologies for safety enhancement (air/liquid/nanofluids/PCM/HP/combinations)',
     'Recent progress + challenges + prospects (qualitative)',
     'Among various BTM types',
     'Comprehensive review',
     'BTM enhances safety via heat transfer intensifying methods',
     'Each TMS has different characteristics; configuration must be examined per application',
     '',
     'medium', 'medium', 'abstract+keywords'],

    # 15. ML+FEM CPCM
    ['doi:10.1016/j.ijheatmasstransfer.2021.121199', 'empirical_ai',
     'Li-ion battery pack with CPCM (paraffin + copper foam)',
     'CNN-based effective thermal property prediction + multiscale FEM model',
     'CNN evaluates BTMS effectiveness with excellent accuracy vs original FEM (qualitative)',
     'Original FEM models + popular CNN architecture',
     'Combined CNN + FEM + Newman battery model + multiscale',
     'CNN predicts CPCM thermal properties accurately for BTMS evaluation',
     'CNN performance comparable to popular image classification networks',
     'Multiscale FEM model based on CNN-predicted properties effective',
     'high', 'medium', 'abstract+keywords'],

    # 16. Hybrid BTMS surrogate optimization
    ['doi:10.1016/j.ijheatmasstransfer.2021.121318', 'empirical_optimization',
     'EV Li-ion battery hybrid BTMS (PCM + liquid + HP)',
     'Surrogate-model-based multi-objective optimization (Adaptive Kriging HDMR + MOPSO)',
     'Best heat dissipation + temp uniformity vs original; prevents thermal runaway propagation under abuse',
     'Original (un-optimized) hybrid BTMS',
     'Numerical heat transfer model + Adaptive Kriging HDMR surrogate + MOPSO',
     'PCM k / PCM thickness / HP length / water velocity significantly affect max temp + ΔT',
     'Optimized hybrid BTMS achieves best heat dissipation + temperature uniformity',
     'Optimization prevents thermal runaway propagation under thermal abuse',
     'high', 'medium', 'abstract+keywords'],

    # 17. Topology optimization cooling plates
    ['doi:10.1016/j.ijheatmasstransfer.2021.121612', 'empirical_optimization',
     'BTMS with cooling plates',
     'Topology optimization of cooling plates (multi-objective: temp diff + pressure drop)',
     'Reduced max temp + temp difference of battery pack (qualitative)',
     'Non-optimized cooling plates',
     'Topology optimization (multi-objective)',
     'Topology optimization improves cooling plate thermal performance',
     'Heat generation rate / inlet flow / material k affect optimal topology',
     'New design approach for BTMS cooling plates',
     'medium', 'medium', 'abstract+keywords'],

    # 18. Thermal coupled battery models review
    ['doi:10.1016/j.ijheatmasstransfer.2023.124748', 'review',
     'EV Li-ion battery thermal coupled models',
     'Various thermal coupled models + parameter identification methods',
     'Model classification + identification methodology insights (qualitative)',
     'Among electrochemical-thermal / electrical-thermal / multi-physics models',
     'Literature review',
     'Thermal coupled battery models classified into 3 categories',
     'Parameter identification methods (experimental + numerical) reviewed',
     '',
     'medium', 'medium', 'abstract+keywords'],

    # 19. Wide temperature + abuse review
    ['doi:10.1016/j.ijhydene.2022.01.008', 'review',
     'Li-ion BTMS for wide temperature range + abuse conditions',
     'Various thermal management strategies (air/liquid/PCM/HP/hybrid)',
     'Review of progress + challenges (qualitative)',
     'Among BTMSs at low/high/abuse conditions',
     'Comprehensive review',
     'Operating temperature significantly affects performance + safety + lifespan',
     'BTMS strategies cover air/liquid/PCM/HP/hybrid',
     'Future directions for extreme conditions identified',
     'medium', 'medium', 'abstract+keywords'],

    # 20. PSO-SVR liquid-cooled BTMS+HPACS
    ['doi:10.1016/j.jpowsour.2021.229727', 'empirical_ai',
     'BEV liquid-cooled BTMS + HPACS coupling system',
     'PSO-SVR surrogate model for cooling capacity + COP prediction',
     'vs SVR: R ↑2.1%/2.8% (cooling cap/COP); MSE ↓87.8%/82.9%',
     'SVR model',
     'Experimental data + automatic calibration + SVR + PSO optimization',
     'PSO-SVR significantly improves prediction accuracy vs plain SVR',
     'Cooling capacity R improved 2.1%; COP R improved 2.8%',
     'MSE reduced 82.9-87.8% across both metrics',
     'high', 'medium', 'abstract+keywords'],

    # 21. Multi-physics immersion cooling
    ['doi:10.1016/j.jpowsour.2025.236285', 'empirical_immersion',
     '18650 cylindrical Li-ion cell under forced immersion cooling',
     'Multi-physics coupled modeling (electrochem + thermal + fluid + mechanical)',
     'Strong cross-coupling identified; new cooling capacity metric defined; insights for design',
     'Deionized water vs mineral oil at 3 flow rates',
     'Fully coupled electrochemical-thermal-fluid model + mechanical stress estimation',
     'Strong cross-coupling between electrochemical and heat transfer phenomena',
     'Novel metric proposed to compare cooling capacity across flow parameters',
     'Mechanical stresses estimated from ion diffusion + temp rise (impacts reliability)',
     'high', 'medium', 'abstract+keywords'],

    # 22. Energy-efficient EV BTMS review
    ['doi:10.1016/j.rser.2021.111611', 'review',
     'EV BTMS for energy efficiency',
     'BTMS technologies (air/liquid/PCM/HP/hybrid)',
     'BTMS overview + challenges + future directions (qualitative)',
     'Among 5 BTMS types',
     'Literature review',
     'Each BTMS has distinct operating principle + trade-offs',
     'BTMS performance affected by multiple parameters',
     'Research gaps + future directions identified',
     'medium', 'medium', 'abstract+keywords'],

    # 23. P-01 (dryrun reused)
    ['doi:10.1016/j.rser.2023.114171', 'review',
     'Commercial EV Li-ion battery packs', 'Air/Liquid/PCM/TEC BTMS',
     'Pros and cons + applicable scenarios',
     '4 BTMS types pairwise', 'Literature review',
     'Air-cooled fits short-range EV; liquid-cooled fits long-range + large pack + high heat',
     'PCM fits constant heat load + stable ambient',
     'TEC best as hybrid component',
     'high', 'low', 'abstract+keywords'],

    # 24. Progress in BTMS review
    ['doi:10.1016/j.rser.2024.114654', 'review',
     'EV Li-ion BTMS (high-capacity)',
     'Various BTMS designs (passive/active/hybrid + various heat transfer mediums)',
     'Progress overview + framework for future R&D (qualitative)',
     'Among PCM types / refrigerants / combinations',
     'Comprehensive review',
     'Latest BTMS designs span passive/active/hybrid models',
     'Heat transfer mediums (PCM/refrigerant/combinations) categorized by material',
     'Fast-charging safety design rarely studied; this review covers it',
     'medium', 'medium', 'abstract+keywords'],

    # 25. Z-type FACS optimization
    ['doi:10.1063/5.0212606', 'empirical_cfd',
     'Li-ion battery pack with Z-type FACS',
     'Z-type FACS optimization (inlet velocity + tapered manifold + 7 secondary outlets)',
     'Inlet 3→4.5 m/s: Tmax ↓4.57°C(10.05%) + δTmax ↓0.29°C(9.79%); 7 sec outlets: Tmax ↓0.894°C(2.18%) + δTmax ↓2.23°C(72.84%)',
     'Original 3 m/s velocity / 0 secondary outlets / non-tapered manifold',
     'CFD simulation + parameter sweep',
     'Higher inlet velocity reduces Tmax + δTmax significantly',
     'Tapered inlet manifold improves cooling for cells 3-9 + uniform airflow',
     '7 secondary outlets reduce δTmax by 72.84%',
     'high', 'medium', 'abstract+keywords'],

    # 26. Physics-informed CNN BTMS
    ['doi:10.1109/rams48127.2025.10935157', 'empirical_ai',
     '21700 battery pack indirect liquid cooling system',
     'Physics-informed CNN surrogate model',
     '>15% accuracy improvement vs data-driven CNN with same training data',
     'Data-driven CNN (same training set)',
     'PI-CNN with heat conduction equation in loss function (via FDM) + simplified FEM training data',
     'Physics-informed loss function helps convergence with less data',
     'PI-CNN >15% accuracy gain over data-driven CNN',
     'Cold plates as constant temp boundaries; battery cells as heat sources',
     'high', 'medium', 'abstract+keywords'],

    # 27. P-04 (dryrun reused)
    ['doi:10.3390/en14164879', 'review',
     'EV Li-ion batteries (cylindrical/prismatic/pouch)',
     'BTMS cooling technologies',
     'Performance + life optimization (qualitative)',
     'Cooling technologies vs battery shapes',
     'Critical literature review',
     'Different shapes need different BTMS designs',
     'Future research directions proposed',
     '',
     'medium', 'medium', 'abstract+keywords'],
]


def main():
    # Existing P-06 abstract row to keep (will be replaced in step 3 with fulltext)
    p06 = ['arxiv:2403.10566', 'empirical_ai',
           'EV battery cell arrangement',
           'Cooling-guided Diffusion Model (DDPM + dual guidance)',
           'Tmax ↓; 5× vs TabDDPM, 66× vs CTGAN',
           'TabDDPM + CTGAN baselines',
           'Generative diffusion + classifier+cooling guidance',
           'DDPM beats baselines by 1+ order of magnitude',
           'Position guidance ensures feasibility',
           'Cooling guidance directly optimizes efficiency',
           'high', 'medium', 'abstract+keywords']

    all_rows = ROWS + [p06]

    with OUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(HEADER)
        for row in all_rows:
            writer.writerow(row)

    print(f"Wrote {len(all_rows)} rows to {OUT}")
    print(f"  abstract-only (step 2): {len(ROWS)}")
    print(f"  arxiv pending fulltext upgrade (step 3): 1 (P-06 placeholder)")

    # Self-check
    from collections import Counter
    confs = Counter(r[10] for r in all_rows)
    print(f"  confidence distribution: {dict(confs)}")

if __name__ == "__main__":
    main()
