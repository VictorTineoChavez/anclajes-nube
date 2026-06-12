import pandas as pd
import re

print("Iniciando Generación de SKUs Inteligentes con Corrección Métrica y UNC...")

try:
    # 1. Leer y limpiar archivo
    df = pd.read_excel('invoice.xlsx')
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.upper()
    
    # 2. Aplanar estructura
    df['CATEGORIA_TEMP'] = df['DESCRIPTIONS'].where(pd.isna(df['QUANTITY (PCS)']))
    df['CATEGORIA_TEMP'] = df['CATEGORIA_TEMP'].ffill()
    df = df.dropna(subset=['QUANTITY (PCS)'])

    # Procesamiento Fila a Fila
    def procesar_fila(row):
        try:
            size_raw = str(row['DESCRIPTIONS']).upper().strip().replace('"', '')
            categoria = str(row['CATEGORIA_TEMP']).upper().strip()
            
            # --- IDENTIFICAR FAMILIAS Y CALIDAD ---
            if '316' in categoria and 'BOLT' in categoria:
                familia, pre_sku, es_perno, cal, su_sku = 'PERNO HEX ASTM 316', 'P316', True, 'INOX', 'I'
            elif '316' in categoria and 'NUT' in categoria:
                familia, pre_sku, es_perno, cal, su_sku = 'TUERCA HEX ASTM 316', 'T316', False, 'INOX', 'I'
            elif 'DIN931' in categoria:
                # Material Métrico detectado
                familia, pre_sku, es_perno, cal, su_sku = 'PERNO HEX DIN931 8.8', 'P931', True, 'GALV.', 'G'
            elif 'A325' in categoria:
                familia, pre_sku, es_perno, cal, su_sku = 'PERNO HEX ASTM A325', 'P325', True, 'GALV.', 'G'
            elif 'B7' in categoria:
                # BARRDS B7 = Espárragos (Varillas Roscadas)
                familia, pre_sku, es_perno, cal, su_sku = 'ESPARRAGO B7', 'E0B7', True, 'F.N', 'N'
            elif '2H' in categoria and 'BLACK' in categoria:
                familia, pre_sku, es_perno, cal, su_sku = 'TUERCA HEX 2H', 'T02H', False, 'F.N', 'N'
            elif '2H' in categoria and 'HDG' in categoria:
                familia, pre_sku, es_perno, cal, su_sku = 'TUERCA HEX 2H', 'T02H', False, 'GALV.', 'G'
            else:
                familia, pre_sku, es_perno, cal, su_sku = 'GENERICO', 'GEN', False, 'S/E', 'X'

            # --- EXTRACCIÓN QUIRÚRGICA DE MEDIDAS ---
            diam_str, largo_str, desc_medida = "", "", ""
            is_metric = 'DIN931' in categoria or 'M' in size_raw

            if is_metric:
                if es_perno:
                    partes = size_raw.split('*')
                    diam_str, largo_str = partes[0], partes[1] if len(partes) > 1 else "0"
                    desc_medida = f"M{diam_str} X {largo_str}MM"
                else:
                    diam_str = size_raw.replace('M', '').strip()
                    largo_str = "0"
                    desc_medida = f"M{diam_str}"
            else:
                if '*' in size_raw:
                    # Es un Perno o Espárrago en pulgadas
                    d_raw, r_raw = size_raw.split('*', 1)
                    
                    # Separar los Hilos (TPI) del diámetro sin romper medidas como 1-1/2
                    d_parts = d_raw.rsplit('-', 1)
                    diam_str = d_parts[0] if len(d_parts) > 1 and len(d_parts[1]) <= 2 else d_raw
                    
                    # Separar los Hilos (TPI) del largo
                    l_parts = r_raw.split('-')
                    largo_str = l_parts[0]

                    # Armar texto visual
                    if 'B7' in categoria:
                        desc_medida = f'{diam_str}" X {largo_str}M'  # Los 3.66 son Metros
                    else:
                        desc_medida = f'{diam_str}" X {largo_str}"'
                else:
                    # Son Tuercas en pulgadas
                    d_parts = size_raw.rsplit('-', 1)
                    diam_str = d_parts[0] if len(d_parts) > 1 and len(d_parts[1]) <= 2 else size_raw
                    largo_str = "0"
                    desc_medida = f'{diam_str}"'

            # --- GENERACIÓN DE SKUS ---
            mapa_diam = {
                '1/2': '12', '5/8': '58', '3/4': '34', '7/8': '78', 
                '1': '10', '1 1/8': '118', '1-1/8': '118', '1 1/4': '114', 
                '1-1/4': '114', '1 3/8': '138', '1-3/8': '138', '1 1/2': '112', 
                '1-1/2': '112', '1 3/4': '134', '1-3/4': '134', '2': '20'
            }
            
            # Codificar Diámetro
            cod_diam = "00"
            if is_metric:
                cod_diam = f"{int(diam_str):02d}" if diam_str.isdigit() else "00"
            else:
                cod_diam = mapa_diam.get(diam_str, re.sub(r'[^0-9]', '', diam_str))
                if not cod_diam: cod_diam = "00"

            # Codificar Largo
            cod_largo = "0000"
            float_len = 0.0
            if es_perno:
                if is_metric:
                    cod_largo = f"{int(largo_str):04d}" if largo_str.isdigit() else "0000"
                elif 'B7' in categoria:
                    float_len = float(largo_str)
                    cod_largo = f"{int(float_len*100):04d}" # Convierte 3.66 a 0366
                else:
                    try:
                        if '/' in largo_str:
                            if '-' in largo_str or ' ' in largo_str:
                                sep = '-' if '-' in largo_str else ' '
                                entero, fraccion = largo_str.split(sep)
                                num, den = fraccion.split('/')
                                float_len = float(entero) + (float(num)/float(den))
                                cod_largo = f"{int(entero):02d}{num.strip()}{den.strip()}"
                            else:
                                num, den = largo_str.split('/')
                                float_len = float(num)/float(den)
                                cod_largo = f"00{num.strip()}{den.strip()}"
                        else:
                            float_len = float(largo_str)
                            cod_largo = f"{int(float_len):02d}00"
                    except:
                        cod_largo = "0000"

            # --- ARMADO DE DESCRIPCIONES PERFECTAS ---
            if es_perno:
                if 'B7' in categoria:
                    # Los espárragos son hilo continuo, no llevan R/C ni R/P
                    sku_final = f"{pre_sku}{su_sku}{cod_diam}{cod_largo}"
                    desc_final = f"{familia} {desc_medida}"
                else:
                    # Lógica de rosca (Asumimos R/P para milimétricos grandes)
                    rosca_txt, rosca_letra = 'R/P', 'P'
                    if not is_metric and float_len > 0 and float_len <= 1.25:
                        rosca_txt, rosca_letra = 'R/C', 'C'
                    
                    sku_final = f"{pre_sku}{su_sku}{cod_diam}{cod_largo}{rosca_letra}"
                    desc_final = f"{familia} {desc_medida} {rosca_txt}"
            else:
                sku_final = f"{pre_sku}{su_sku}{cod_diam}"
                desc_final = f"{familia} {desc_medida}"

            return pd.Series([sku_final, desc_final, familia, cal])
            
        except Exception as err_fila:
            print(f"⚠️ Aviso: Fila ignorada ({row['DESCRIPTIONS']}) - Error: {str(err_fila)}")
            return pd.Series(["ERROR", "ERROR", "ERROR", "ERROR"])

    # Aplicar y limpiar
    print("Separando diámetros de hilos UNC y detectando varillas B7...")
    df[['CÓDIGO_GEN', 'DESCRIPCIÓN_GEN', 'FAMILIA_GEN', 'CALIDAD_GEN']] = df.apply(procesar_fila, axis=1)
    df = df[df['CÓDIGO_GEN'] != 'ERROR']

    # 3. Agrupar
    resumen = df.groupby(['CÓDIGO_GEN', 'DESCRIPCIÓN_GEN', 'FAMILIA_GEN', 'CALIDAD_GEN']).agg(
        STOCK=('QUANTITY (PCS)', 'sum')
    ).reset_index()

    # 4. Exportar a formato Anclajes y Pernos Perú
    final_df = pd.DataFrame()
    final_df['CÓDIGO'] = resumen['CÓDIGO_GEN']
    final_df['DESCRIPCIÓN'] = resumen['DESCRIPCIÓN_GEN']
    final_df['FAMILIA'] = resumen['FAMILIA_GEN']
    final_df['UBICACION'] = "POR ASIGNAR" 
    final_df['CALIDAD'] = resumen['CALIDAD_GEN']
    final_df['CANT. ACT.'] = resumen['STOCK']
    final_df['STOCK MÍNIMO'] = 10
    final_df['P. UNIT'] = 0.00
    final_df['P. CAJA'] = 0.00
    final_df['ACCIONES'] = ""

    nombre_archivo = 'Inventario_Inteligente_Anclajes_y_Pernos.xlsx'
    final_df.to_excel(nombre_archivo, index=False)
    
    print(f"✅ ÉXITO: Inventario de Anclajes y Pernos Perú generado sin errores en '{nombre_archivo}'")

except Exception as e:
    print(f"❌ ERROR: {str(e)}")