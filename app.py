# Continuing the fixed code from where it cut off

continuation = '''            t_col("User", lang): k,
            t_col("Role", lang): v.get('role', 'viewer')
        })
    
    df_users = pd.DataFrame(table_data)
    st.dataframe(style_df(df_users), use_container_width=True)

def render_order_processing_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.title(f" {t('order_processing_title', lang)}")
    
    loading_placeholder = show_loading_hourglass()
    
    try:
        customers_df = st.session_state.db.fetch_customer_requests()
        workers_df = st.session_state.db.fetch_data()
    except Exception as e:
        loading_placeholder.empty()
        st.error(f"{t('error', lang)}: {e}")
        return
    
    loading_placeholder.empty()
    
    if customers_df.empty:
        st.warning(t("no_data", lang))
        return
    
    if workers_df.empty:
        st.warning("لا توجد بيانات عمال" if lang == 'ar' else "No worker data available")
        return

    def find_cust_col(keywords):
        for c in customers_df.columns:
            c_lower = str(c).lower()
            if all(kw in c_lower for kw in keywords): return c
        return None
    
    c_company = find_cust_col(["company"]) or find_cust_col(["شركه"]) or find_cust_col(["مؤسس"])
    c_responsible = find_cust_col(["responsible"]) or find_cust_col(["مسؤول"])
    c_mobile = find_cust_col(["mobile"]) or find_cust_col(["موبيل"])
    c_category = find_cust_col(["category"]) or find_cust_col(["فئ"])
    c_nationality = find_cust_col(["nationality"]) or find_cust_col(["جنسي"])
    c_location = find_cust_col(["location"]) or find_cust_col(["موقع"])
    c_num_emp = find_cust_col(["number of employees"]) or find_cust_col(["عدد"])
    c_work_nature = find_cust_col(["nature"]) or find_cust_col(["طبيعة"])
    c_salary = find_cust_col(["salary"]) or find_cust_col(["راتب"])
    
    w_name_col = next((c for c in workers_df.columns if "full name" in c.lower()), None)
    w_nationality_col = next((c for c in workers_df.columns if c.strip().lower() == "nationality"), None)
    w_gender_col = next((c for c in workers_df.columns if c.strip().lower() == "gender"), None)
    w_job_col = next((c for c in workers_df.columns if "job" in c.lower() and "looking" in c.lower()), None)
    w_city_col = next((c for c in workers_df.columns if "city" in c.lower() and "saudi" in c.lower()), None)
    w_phone_col = next((c for c in workers_df.columns if "phone" in c.lower()), None)
    w_age_col = next((c for c in workers_df.columns if "age" in c.lower()), None)

    import re
    
    def normalize(text):
        if not text: return ""
        s = str(text).strip().lower()
        s = re.sub(r'[^\w\s\-]', ' ', s, flags=re.UNICODE)
        return ' '.join(s.split()).strip()
    
    def match_gender(customer_category, worker_gender):
        cat = normalize(customer_category)
        gen = normalize(worker_gender)
        if not cat or not gen: return True
        is_male_request = ("رجال" in cat) or (re.search(r'\bmale\b', cat) and "female" not in cat)
        is_female_request = ("نساء" in cat) or ("female" in cat)
        if is_male_request:
            return re.search(r'\bmale\b', gen) is not None and "female" not in gen
        elif is_female_request:
            return "female" in gen
        return True
    
    def match_nationality(customer_nat, worker_nat):
        c_raw = str(customer_nat).strip()
        w_nat = normalize(worker_nat)
        if not c_raw or not w_nat: return True
        parts = [p.strip() for p in c_raw.split(',')]
        for part in parts:
            pn = normalize(part)
            if w_nat in pn or pn in w_nat:
                return True
            words = re.split(r'[\s\-–|]+', pn)
            for word in words:
                word = word.strip()
                if len(word) > 2 and (word in w_nat or w_nat in word):
                    return True
        return False
    
    def match_job(customer_job, worker_job):
        c_job = normalize(customer_job)
        w_job = normalize(worker_job)
        if not c_job or not w_job: return True
        requested_jobs = [j.strip() for j in c_job.split(',')]
        for rj in requested_jobs:
            rj = normalize(rj)
            if rj and len(rj) > 1 and (rj in w_job or w_job in rj):
                return True
        return False
    
    def match_city(customer_location, worker_city):
        c_loc = normalize(customer_location)
        w_city_val = normalize(worker_city)
        if not c_loc or not w_city_val: return True
        parts = re.split(r'[|,،]+', c_loc)
        for part in parts:
            part = part.strip()
            if part and len(part) > 1 and (part in w_city_val or w_city_val in part):
                return True
        return False
    
    def find_matching_workers(customer_row):
        city_matches, city_scores = [], []
        other_matches, other_scores = [], []
        
        for _, worker in workers_df.iterrows():
            score = 0
            total_criteria = 0
            city_matched = False
            
            if c_category and w_gender_col:
                cv = str(customer_row.get(c_category, ""))
                wv = str(worker.get(w_gender_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_gender(cv, wv): score += 1
            
            if c_nationality and w_nationality_col:
                cv = str(customer_row.get(c_nationality, ""))
                wv = str(worker.get(w_nationality_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_nationality(cv, wv): score += 1
            
            if c_work_nature and w_job_col:
                cv = str(customer_row.get(c_work_nature, ""))
                wv = str(worker.get(w_job_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_job(cv, wv): score += 1
            
            if c_location and w_city_col:
                cv = str(customer_row.get(c_location, ""))
                wv = str(worker.get(w_city_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_city(cv, wv):
                        score += 1
                        city_matched = True
            
            if total_criteria > 0 and score >= 1:
                pct = int((score / total_criteria) * 100)
                if city_matched:
                    city_matches.append(worker)
                    city_scores.append(pct)
                else:
                    other_matches.append(worker)
                    other_scores.append(pct)
        
        if city_matches:
            paired = sorted(zip(city_scores, range(len(city_matches)), city_matches), key=lambda x: -x[0])
            city_scores = [p[0] for p in paired]
            city_matches = [p[2] for p in paired]
        if other_matches:
            paired = sorted(zip(other_scores, range(len(other_matches)), other_matches), key=lambda x: -x[0])
            other_scores = [p[0] for p in paired]
            other_matches = [p[2] for p in paired]
        
        return city_matches + other_matches, city_scores + other_scores, len(city_matches)

    if 'op_hidden_clients' not in st.session_state:
        st.session_state.op_hidden_clients = set()
    if 'op_hidden_workers' not in st.session_state:
        st.session_state.op_hidden_workers = set()

    if st.session_state.op_hidden_workers:
        if st.sidebar.button("🔓 " + ("أظهر جميع العمال المخفيين" if lang == 'ar' else "Show all hidden workers")):
            st.session_state.op_hidden_workers.clear()
            st.rerun()

    def build_worker_table(worker_list, score_list):
        rows = []
        filtered_indices = []
        for i, (worker, score) in enumerate(zip(worker_list, score_list)):
            w_name = str(worker.get(w_name_col, "")) if w_name_col else ""
            w_phone = str(worker.get(w_phone_col, "")) if w_phone_col else ""
            worker_uid = hashlib.md5(f"{w_name}{w_phone}".encode()).hexdigest()
            
            if worker_uid in st.session_state.op_hidden_workers:
                continue
                
            row = {}
            row[t('match_score', lang)] = f"{score}%"
            if w_name_col: row[t('worker_name', lang)] = w_name
            if w_nationality_col: row[t('worker_nationality', lang)] = str(worker.get(w_nationality_col, ""))
            if w_gender_col: row[t('worker_gender', lang)] = str(worker.get(w_gender_col, ""))
            if w_job_col: row[t('worker_job', lang)] = str(worker.get(w_job_col, ""))
            if w_city_col: row[t('worker_city', lang)] = str(worker.get(w_city_col, ""))
            if w_phone_col: row[t('worker_phone', lang)] = w_phone
            if w_age_col: row[t('worker_age', lang)] = str(worker.get(w_age_col, ""))
            
            row["__uid"] = worker_uid
            rows.append(row)
            filtered_indices.append(i)
            
        return pd.DataFrame(rows), filtered_indices

    def info_cell(icon, label_text, value, color="#F4F4F4"):
        st.markdown(f"""
            <div style="background: rgba(255,255,255,0.04); padding: 12px; border-radius: 10px;
                        border: 1px solid rgba(255,255,255,0.06); margin: 5px 0; min-height: 80px;">
                <span style="color: #888; font-size: 0.8rem;">{label_text}</span><br>
                <span style="color: {color}; font-size: 1.1rem; font-weight: 600;">{icon} {value}</span>
            </div>
        """, unsafe_allow_html=True)

    c_timestamp = find_cust_col(["timestamp"]) or find_cust_col(["الطابع"]) or find_cust_col(["تاريخ"])
    if not c_timestamp and len(customers_df.columns) > 0:
        c_timestamp = customers_df.columns[0]

    st.markdown("### 📋 " + t('customer_requests', lang))
    
    for idx, customer_row in customers_df.iterrows():
        company_val = str(customer_row.get(c_company, "")) if c_company else ""
        responsible_val = str(customer_row.get(c_responsible, "")) if c_responsible else ""
        client_key = f"client_{idx}"
        
        display_name = f"{company_val} - {responsible_val}".strip(" -")
        if not display_name: display_name = f"طلب #{idx+1}" if lang == 'ar' else f"Request #{idx+1}"
        
        is_visible = st.checkbox(
            f"✅ {display_name}", 
            value=(client_key not in st.session_state.op_hidden_clients),
            key=f"op_vis_check_{idx}"
        )
        
        if not is_visible:
            st.session_state.op_hidden_clients.add(client_key)
            st.divider()
            continue
        else:
            st.session_state.op_hidden_clients.discard(client_key)
            
        with st.container():
            st.markdown(f"""
                <div style="background: linear-gradient(90deg, rgba(212,175,55,0.15), transparent); 
                            padding: 10px 20px; border-radius: 10px; border-left: 5px solid #D4AF37; margin: 15px 0 5px 0;">
                    <h3 style="color: #D4AF37; margin: 0; font-family: 'Tajawal', sans-serif;">🏢 {company_val} <span style="font-size: 0.8rem; color: #888;">#{idx+1}</span></h3>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if c_timestamp: info_cell("📅", "التاريخ" if lang == 'ar' else "Date", str(customer_row.get(c_timestamp, "")))
                info_cell("📍", t('work_location', lang), str(customer_row.get(c_location, "")))
                info_cell("💼", t('work_nature', lang), str(customer_row.get(c_work_nature, "")))
            with col2:
                info_cell("👤", t('responsible_name', lang), responsible_val)
                info_cell("👥", t('required_category', lang), str(customer_row.get(c_category, "")))
                info_cell("🔢", t('num_employees', lang), str(customer_row.get(c_num_emp, "")), "#D4AF37")
            with col3:
                info_cell("📱", t('mobile_number', lang), str(customer_row.get(c_mobile, "")))
                info_cell("🌍", t('required_nationality', lang), str(customer_row.get(c_nationality, "")))
                info_cell("💰", t('expected_salary', lang), str(customer_row.get(c_salary, "")), "#00FF41")

            matches, scores, city_count = find_matching_workers(customer_row)
            
            if not matches:
                st.warning("⚠️ " + t('no_matching_workers', lang))
            else:
                city_list = matches[:city_count]
                other_list = matches[city_count:]
                city_scores = scores[:city_count]
                other_scores = scores[city_count:]

                if city_list:
                    city_df, city_idx_map = build_worker_table(city_list, city_scores)
                    if not city_df.empty:
                        st.markdown(f"""<div style="color: #D4AF37; font-weight: 700; margin: 10px 5px;">📍 عمال في نفس المدينة ({str(customer_row.get(c_location, ""))}) — {len(city_df)}</div>""", unsafe_allow_html=True)
                        
                        st.markdown("""
                            <style>
                            .stDataFrame {
                                overflow-x: auto !important;
                            }
                            .stDataFrame > div {
                                overflow-x: auto !important;
                                min-width: 100%;
                            }
                            </style>
                        """, unsafe_allow_html=True)
                        
                        df_city_height = min((len(city_df) + 1) * 35 + 40, 500)
                        event_city = st.dataframe(
                            city_df.drop(columns=["__uid"]),
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            key=f"op_city_table_{idx}",
                            height=df_city_height
                        )
                        
                        if event_city.selection and event_city.selection.get("rows"):
                            sel_row_idx = event_city.selection["rows"][0]
                            original_idx = city_idx_map[sel_row_idx]
                            worker_row = city_list[original_idx]
                            worker_uid = city_df.iloc[sel_row_idx]["__uid"]
                            
                            render_cv_detail_panel(worker_row, sel_row_idx, lang, key_prefix=f"op_city_{idx}")
                            
                            if st.button("🚫 " + ("إخفاء هذا العامل" if lang == 'ar' else "Hide this worker"), 
                                         key=f"hide_city_{idx}_{worker_uid}"):
                                st.session_state.op_hidden_workers.add(worker_uid)
                                st.rerun()

                if other_list:
                    other_df, other_idx_map = build_worker_table(other_list, other_scores)
                    if not other_df.empty:
                        st.markdown(f"""<div style="color: #8888FF; font-weight: 700; margin: 10px 5px;">🌐 عمال في مدن أخرى — {len(other_df)}</div>""", unsafe_allow_html=True)
                        
                        st.markdown("""
                            <style>
                            .stDataFrame {
                                overflow-x: auto !important;
                            }
                            .stDataFrame > div {
                                overflow-x: auto !important;
                                min-width: 100%;
                            }
                            </style>
                        """, unsafe_allow_html=True)
                        
                        df_other_height = min((len(other_df) + 1) * 35 + 40, 500)
                        event_other = st.dataframe(
                            other_df.drop(columns=["__uid"]),
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            key=f"op_other_table_{idx}",
                            height=df_other_height
                        )
                        
                        if event_other.selection and event_other.selection.get("rows"):
                            sel_row_idx = event_other.selection["rows"][0]
                            original_idx = other_idx_map[sel_row_idx]
                            worker_row = other_list[original_idx]
                            worker_uid = other_df.iloc[sel_row_idx]["__uid"]
                            
                            render_cv_detail_panel(worker_row, sel_row_idx, lang, key_prefix=f"op_other_{idx}")
                            
                            if st.button("🚫 " + ("إخفاء هذا العامل" if lang == 'ar' else "Hide this worker"), 
                                         key=f"hide_other_{idx}_{worker_uid}"):
                                st.session_state.op_hidden_workers.add(worker_uid)
                                st.rerun()
                
                if (not city_list or build_worker_table(city_list, city_scores)[0].empty) and \
                   (not other_list or build_worker_table(other_list, other_scores)[0].empty):
                    st.info("تم إخفاء جميع العمال المطابقين لهذا الطلب.")

            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            st.divider()



def render_customer_requests_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.title(f" {t('customer_requests_title', lang)}")
    
    loading_placeholder = show_loading_hourglass()
    try:
        df = st.session_state.db.fetch_customer_requests()
    except Exception as e:
        loading_placeholder.empty()
        import traceback
        full_err = traceback.format_exc()
        err_msg = str(e)
        
        is_permission_error = any(kw in err_msg.lower() or kw in full_err.lower() 
                                for kw in ["403", "permission", "not found", "gspread", "api"])

        if not err_msg:
            err_msg = "Connection or Permission Error" if is_permission_error else "Technical Error (Details below)"
            
        st.error(f"{t('error', lang)}: {err_msg}")
        
        st.warning("⚠️ إعدادات الربط غير مكتملة أو الملف غير متاح")
        st.info("لحل هذه المشكلة، يرجى التأكد من **مشاركة (Share)** ملف الإكسل مع هذا البريد الإلكتروني كـ **Editor**:")
        st.code("sheet-bot@smooth-league-454322-p2.iam.gserviceaccount.com")
        
        with st.expander("Show Technical Details | تفاصيل الخطأ التقنية"):
            st.code(full_err)
            
        if "REPLACE_WITH_CUSTOMER_REQUESTS_SHEET_URL" in err_msg or "URL" in err_msg:
            st.info("⚠️ يرجى تزويد المبرمج برابط ملف جوجل شيت (Spreadsheet) الخاص بتبويب 'الردود' في النموذج لإتمام الربط.")
        
        st.markdown("""
        **خطوات التأكد من الربط:**
        1. افتح ملف جوجل شيت (الذي سجلت فيه ردود النموذج).
        2. اضغط على زر **Share** (مشاركة) في الزاوية العلوية.
        3. انسخ هذا الإيميل: `sheet-bot@smooth-league-454322-p2.iam.gserviceaccount.com`
        4. أضف الإيميل وتأكد من اختيار **Editor** (محرر).
        5. اضغط على زر **Send** (إرسال).
        6. عد هنا وقم بـ **تحديث الصفحة (Refresh)**.
        """)
        return

    loading_placeholder.empty()

    if df.empty:
        st.warning(t("no_data", lang))
        return

    res = df.copy()
    
    new_names = {}
    used_names = set()
    for c in res.columns:
        new_name = t_col(c, lang)
        original_new_name = new_name
        counter = 1
        while new_name in used_names:
            counter += 1
            new_name = f"{original_new_name} ({counter})"
        used_names.add(new_name)
        new_names[c] = new_name
        
    res.rename(columns=new_names, inplace=True)
    res = clean_date_display(res)
    
    res_display = res.copy()
    for int_col in ["__sheet_row", "__sheet_row_backup"]:
        if int_col in res_display.columns:
            res_display = res_display.drop(columns=[int_col])
            
    st.markdown("""
        <style>
        .stDataFrame {
            overflow-x: auto !important;
        }
        .stDataFrame > div {
            overflow-x: auto !important;
            min-width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.dataframe(
        style_df(res_display), 
        use_container_width=True,
        hide_index=True,
        key="customer_requests_table"
    )

if not st.session_state.user:
    login_screen()
else:
    dashboard()
'''

print(continuation)
