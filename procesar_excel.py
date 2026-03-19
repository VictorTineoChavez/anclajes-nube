import pandas as pd
import re

print("Iniciando Generación de SKUs Inteligentes...")

try:
    # 1. Leer y limpiar archivo
    df = pd.read_excel('packing.xlsx')
    df.columns = df.columns.str.strip().str.upper()
    df = df.dropna(subset=['ITEM'])

    # Función a prueba de fallos para decodificar medidas
    def decodificar_medida(size_str, es_perno):
        size_str = str(size_str).strip().replace('"', '')
        
        # Si la celda está vacía o dice NAN
        if size_str.lower() == 'nan' or size_str == '':
            return "00", "0000", 0.0

        # Separar diámetro y largo de forma segura
        if not es_perno:
            diam_str = size_str.split('-')[0].strip() if '-' in size_str else size_str.strip()
            largo_str = "0"
        else:
            if '*' in size_str:
                partes = size_str.split('*')
                diam_str = partes[0].strip()
                # Si hay algo después del asterisco lo tomamos, sino es 0
                largo_str = partes[1].strip() if len(partes) > 1 and partes[1].strip() != '' else "0"
            else:
                diam_str = size_str
                largo_str = "0"

        # Mapa de diámetros a códigos (1/2 -> 12)
        mapa_diam = {
            '1/2': '12', '5/8': '58', '3/4': '34', '7/8': '78', 
            '1': '10', '1 1/8': '118', '1-1/8': '118', '1 1/4': '114', 
            '1-1/4': '114', '1 3/8': '138', '1-3/8': '138', '1 1/2': '112', 
            '1-1/2': '112', '1 3/4': '134', '1-3/4': '134', '2': '20'
        }
        # Si no está en el mapa, quitamos letras y símbolos raros
        cod_diam = mapa_diam.get(diam_str, re.sub(r'[^0-9]', '', diam_str))
        if not cod_diam: cod_diam = "00"

        if not es_perno:
            return cod_diam, "0000", 0.0

        # Calcular el largo de forma ultra-segura
        float_len = 0.0
        cod_largo = "0000"

        try:
            if '-' in largo_str or ' ' in largo_str:
                sep = '-' if '-' in largo_str else ' '
                l_parts = largo_str.split(sep)
                entero = l_parts[0].strip() if l_parts[0].strip() else "0"
                fraccion = l_parts[1].strip() if len(l_parts) > 1 else ""
                
                if '/' in fraccion:
                    num, den = fraccion.split('/')
                    float_len = float(entero) + (float(num) / float(den))
                    cod_largo = f"{int(entero):02d}{num.strip()}{den.strip()}" # Ej: 4-1/2 -> 0412
                else:
                    float_len = float(entero)
                    cod_largo = f"{int(entero):02d}00"
            elif '/' in largo_str:
                num, den = largo_str.split('/')
                float_len = float(num) / float(den)
                cod_largo = f"00{num.strip()}{den.strip()}" # Ej: 1/2 -> 0012
            else:
                float_len = float(largo_str)
                cod_largo = f"{int(float_len):02d}00" # Ej: 1 -> 0100
        except Exception:
            # Si a pesar de todo falla (letras raras, texto corrupto), no colapsa, devuelve 0
            float_len = 0.0
            cod_largo = "0000"

        return cod_diam, cod_largo, float_len

    # Procesar fila individual (Aislada para no tumbar el programa entero)
    def procesar_fila(row):
        try:
            item = str(row['ITEM']).upper()
            size = str(row['SIZE']).upper()
            finish = str(row['FINISH']).upper().strip()
            
            # Familias y Prefijos
            if 'A325' in item: 
                familia, pre_sku, es_perno = 'PERNO HEX. A325', 'P325', True
            elif 'A490' in item:
                familia, pre_sku, es_perno = 'PERNO HEX. A490', 'P490', True
            elif 'NUT' in item:
                familia, pre_sku, es_perno = 'TUERCA HEX. A563', 'T563', False
            else:
                familia, pre_sku, es_perno = item, 'GEN', False

            # Calidad
            if finish == 'BLACK': cal, su_sku = 'F.N', 'N'
            elif finish == 'HDG': cal, su_sku = 'GALV.', 'G'
            else: cal, su_sku = finish, 'X'

            # Códigos de Medidas
            cod_diam, cod_largo, float_len = decodificar_medida(size, es_perno)

            # Lógica de Rosca y Armado Final
            if es_perno:
                # REGLA: <= 1.25" = R/C. Sino R/P.
                rosca_letra = 'C' if float_len <= 1.25 else 'P'
                rosca_txt = 'R/C' if rosca_letra == 'C' else 'R/P'
                
                sku_final = f"{pre_sku}{su_sku}{cod_diam}{cod_largo}{rosca_letra}"
                
                size_visual = size.replace('*', '" X ') + '"' if '*' in size else size
                desc_final = f"{familia.replace('PERNO HEX.', 'PERNO HEX ASTM')} {size_visual} {rosca_txt}"
            else:
                sku_final = f"{pre_sku}{su_sku}{cod_diam}"
                desc_final = f"{familia.replace('TUERCA HEX.', 'TUERCA HEX ASTM')} {size}"

            return pd.Series([sku_final, desc_final, familia, cal])
            
        except Exception as err_fila:
            print(f"⚠️ Aviso: Fila ignorada por formato inválido ({row['SIZE']})")
            return pd.Series(["ERROR", "ERROR", "ERROR", "ERROR"])

    # 2. Aplicar la función a cada fila
    print("Analizando medidas y aplicando reglas de ingeniería...")
    df[['CÓDIGO_GEN', 'DESCRIPCIÓN_GEN', 'FAMILIA_GEN', 'CALIDAD_GEN']] = df.apply(procesar_fila, axis=1)

    # Filtrar las que hayan dado error grave
    df = df[df['CÓDIGO_GEN'] != 'ERROR']

    # 3. Agrupar y sumar
    resumen = df.groupby(['CÓDIGO_GEN', 'DESCRIPCIÓN_GEN', 'FAMILIA_GEN', 'CALIDAD_GEN']).agg(
        STOCK=('QTY', 'sum'),
        UBICACION=('PALLET NO.', lambda x: 'PALLETS: ' + ', '.join(x.dropna().astype(str).unique()))
    ).reset_index()

    # 4. Formato Oficial
    final_df = pd.DataFrame()
    final_df['CÓDIGO'] = resumen['CÓDIGO_GEN']
    final_df['DESCRIPCIÓN'] = resumen['DESCRIPCIÓN_GEN']
    final_df['FAMILIA'] = resumen['FAMILIA_GEN']
    final_df['UBICACION'] = resumen['UBICACION']
    final_df['CALIDAD'] = resumen['CALIDAD_GEN']
    final_df['CANT. ACT.'] = resumen['STOCK']
    final_df['STOCK MÍNIMO'] = 10
    final_df['P. UNIT'] = 0.00
    final_df['P. CAJA'] = 0.00
    final_df['ACCIONES'] = ""

    nombre_archivo = 'Inventario_Inteligente_ImportBolts.xlsx'
    final_df.to_excel(nombre_archivo, index=False)
    
    print(f"✅ ÉXITO TOTAL: {len(final_df)} SKUs únicos generados y guardados en '{nombre_archivo}'")

except Exception as e:
    print(f"❌ ERROR INESPERADO AL LEER EL ARCHIVO: {str(e)}")