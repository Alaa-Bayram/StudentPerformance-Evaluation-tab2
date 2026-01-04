import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(page_title="School Performance Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }

    /* Custom KPI Card Styles */
    .kpi-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        flex: 1;
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-top: 5px solid #ddd;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .kpi-label {
        color: #666;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1f1f1f;
    }
    .kpi-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }

    /* Card Specific Colors */
    .card-blue { border-top-color: #4A90E2; }
    .card-green { border-top-color: #6BCB77; }
    .card-red { border-top-color: #FF6B6B; }
    .card-orange { border-top-color: #FF8C42; }

    /* Search Section Styling */
    .search-container {
        background-color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }

    /* Blue Info Box */
    .blue-info-box {
        background-color: #E3F2FD;
        border-left: 5px solid #2196F3;
        padding: 1rem;
        border-radius: 4px;
        color: #0D47A1;
        font-size: 1.1rem;
        margin-top: 1rem;
        display: flex;
        align-items: center;
    }

    h1 { color: #1f1f1f; font-weight: 700; }
    h2, h3 { color: #2c2c2c; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('Students_Dataset.csv')
    return df


# ==================== STUDENT PERFORMANCE INDEX (SPI) CALCULATION ====================
# This function replaces simple threshold-based classification with a composite scoring system
# that considers multiple factors: academics, attendance, engagement, failures, and trends.
# 
# WHY THIS IS BETTER:
# - Multi-dimensional: Considers 5 factors instead of just 2
# - Weighted appropriately: Academics (60%) > Attendance (25%) > Engagement (15%)
# - Accounts for course failures: Penalizes students failing multiple courses
# - Trend-aware: Identifies students whose performance is declining
# - More granular: 4 levels instead of 3, better differentiation
# - Explainable: Clear formula that can be communicated to stakeholders

def calculate_student_performance_index(student_data, passing_score=60):
    """
    Calculate Student Performance Index (SPI) for a given student.

    Parameters:
    - student_data: DataFrame containing all records for one student
    - passing_score: Threshold for passing (default 60)

    Returns:
    - spi_score: Final SPI score (0-100 scale)
    - status: Classification level
    - status_color: Color code for visualization
    - details: Dictionary with breakdown of components
    """

    # Component 1: Academic Performance (60% weight)
    avg_score = student_data['assessment_score'].mean()
    academic_component = avg_score * 0.60

    # Component 2: Attendance Rate (25% weight)
    avg_attendance = student_data['attendance_rate'].mean()
    attendance_component = avg_attendance * 0.25

    # Component 3: Engagement Score (15% weight)
    # Normalize engagement: assume max meaningful engagement = 30 hand raises
    avg_engagement = student_data['raised_hand_count'].mean()
    normalized_engagement = min(avg_engagement / 30 * 100, 100)  # Cap at 100
    engagement_component = normalized_engagement * 0.15

    # Base SPI (before penalties)
    base_spi = academic_component + attendance_component + engagement_component

    # Penalty 1: Failing Courses
    courses_performance = student_data.groupby('course_name')['assessment_score'].mean()
    failed_courses = (courses_performance < passing_score).sum()

    if failed_courses == 1:
        failure_penalty = 5
    elif failed_courses >= 2:
        failure_penalty = 10
    else:
        failure_penalty = 0

    # Penalty 2: Declining Performance Trend
    assessment_scores = student_data.groupby('assessment_no')['assessment_score'].mean()
    trend_penalty = 0
    performance_change = 0

    if len(assessment_scores) >= 2:
        first_avg = assessment_scores.iloc[0]
        last_avg = assessment_scores.iloc[-1]
        performance_change = last_avg - first_avg

        if performance_change < -10:  # Dropped by more than 10 points
            trend_penalty = 5

    # Final SPI Calculation
    spi_score = base_spi - failure_penalty - trend_penalty
    spi_score = max(0, min(100, spi_score))  # Ensure SPI stays within 0-100

    # Classification based on SPI
    if spi_score >= 80:
        status = "EXCELLENT"
        status_color = "#2E7D32"  # Dark green
    elif spi_score >= 65:
        status = "SATISFACTORY"
        status_color = "#F57C00"  # Amber
    elif spi_score >= 50:
        status = "AT RISK"
        status_color = "#EF6C00"  # Orange
    else:
        status = "CRITICAL"
        status_color = "#C62828"  # Red

    # Details for transparency
    details = {
        'base_spi': base_spi,
        'academic_component': academic_component,
        'attendance_component': attendance_component,
        'engagement_component': engagement_component,
        'failure_penalty': failure_penalty,
        'trend_penalty': trend_penalty,
        'failed_courses': failed_courses,
        'performance_trend': performance_change,
        'normalized_engagement': normalized_engagement
    }

    return spi_score, status, status_color, details


# ==================== END SPI CALCULATION ====================


try:
    df = load_data()

    # Data preprocessing
    df['student_name'] = df['student_name'].str.strip()
    df['course_name'] = df['course_name'].str.strip()
    df['class_level'] = df['class_level'].str.strip()

    # Passing threshold is 60
    PASSING_SCORE = 60

    # Calculate derived metrics
    df['is_passing'] = df['assessment_score'] >= PASSING_SCORE
    df['engagement_score'] = df['raised_hand_count'] + df['moodle_views'] + df['resources_downloads']

    # Overall metrics calculation
    overall_avg = df['assessment_score'].mean()
    pass_rate = (df.groupby('student_id')['is_passing'].mean() * 100).mean()
    fail_rate = 100 - pass_rate
    avg_attendance = df['attendance_rate'].mean()

    # Header
    st.title("School Performance Dashboard")
    current_year = datetime.now().year
    st.markdown(
        f"**Academic Year {current_year - 1} - {current_year}** • Last Updated: {datetime.now().strftime('%B %d, %Y')}")
    st.markdown("---")

    # Enhanced KPI Section
    st.header("Performance Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card card-blue">
            <div class="kpi-icon">📈</div>
            <div class="kpi-label">Overall Average</div>
            <div class="kpi-value">{overall_avg:.1f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card card-green">
            <div class="kpi-icon">👥</div>
            <div class="kpi-label">Pass Rate</div>
            <div class="kpi-value">{pass_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card card-red">
            <div class="kpi-icon">⚠️</div>
            <div class="kpi-label">Fail Rate</div>
            <div class="kpi-value">{fail_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card card-orange">
            <div class="kpi-icon">📚</div>
            <div class="kpi-label">Avg Attendance</div>
            <div class="kpi-value">{avg_attendance:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Score Distribution
    st.header("Score Distribution")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Assessment Score Histogram")
        bins = [0, 40, 60, 80, 100]
        labels = ['0-40', '40-60', '60-80', '80-100']
        df['score_range'] = pd.cut(df['assessment_score'], bins=bins, labels=labels, include_lowest=True)
        score_dist = df['score_range'].value_counts().sort_index()

        fig_hist = go.Figure(data=[
            go.Bar(x=score_dist.index, y=score_dist.values,
                   text=score_dist.values,
                   textposition='outside',
                   textfont=dict(size=14, color='#1f1f1f'),
                   marker_color=['#FF6B6B', '#FFA07A', '#FFD93D', '#6BCB77'])
        ])
        fig_hist.update_layout(
            xaxis_title="Score Range",
            yaxis_title="Number of Assessments",
            height=400,
            margin=dict(l=40, r=40, t=60, b=60),
            showlegend=False,
            yaxis=dict(range=[0, score_dist.max() * 1.15])
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        st.subheader("Class Level Performance Comparison")
        class_performance = df.groupby('class_level')['assessment_score'].mean().reset_index()
        class_counts = df.groupby('class_level').size().reset_index(name='count')

        fig_class = go.Figure(data=[
            go.Bar(x=class_performance['class_level'],
                   y=class_performance['assessment_score'],
                   text=class_performance['assessment_score'].round(1),
                   textposition='outside',
                   textfont=dict(size=14, color='#1f1f1f'),
                   marker_color=['#4A90E2', '#50C878', '#FF8C42', '#9B59B6', '#FFD93D'])
        ])
        fig_class.add_hline(y=PASSING_SCORE, line_dash="dash", line_color="red",
                            annotation_text="Passing (60)", annotation_position="right")
        fig_class.update_layout(
            xaxis_title="Class Level",
            yaxis_title="Average Score",
            height=400,
            margin=dict(l=40, r=40, t=60, b=60),
            showlegend=False,
            yaxis=dict(range=[0, class_performance['assessment_score'].max() * 1.15])
        )
        st.plotly_chart(fig_class, use_container_width=True)

    st.markdown("---")

    # Performance by Structure
    st.header("Performance by Structure")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Resource Usage by Class Level")

        # Calculate average resource usage by class level
        resource_usage = df.groupby('class_level').agg({
            'moodle_views': 'mean',
            'resources_downloads': 'mean'
        }).reset_index()

        fig_resources = go.Figure()

        # Add Moodle Views bars
        fig_resources.add_trace(go.Bar(
            name='Moodle Views',
            x=resource_usage['class_level'],
            y=resource_usage['moodle_views'],
            marker_color='#4A90E2',
            text=resource_usage['moodle_views'].round(1),
            textposition='inside',
            textfont=dict(size=12, color='white')
        ))

        # Add Resource Downloads bars
        fig_resources.add_trace(go.Bar(
            name='Downloads',
            x=resource_usage['class_level'],
            y=resource_usage['resources_downloads'],
            marker_color='#FF8C42',
            text=resource_usage['resources_downloads'].round(1),
            textposition='inside',
            textfont=dict(size=12, color='white')
        ))

        fig_resources.update_layout(
            barmode='group',
            height=400,
            xaxis_title="Class Level",
            yaxis_title="Average Count",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=40, r=40, t=40, b=60)
        )
        st.plotly_chart(fig_resources, use_container_width=True)

    with col2:
        st.subheader("Average Score by Course")
        course_avg = df.groupby('course_name')['assessment_score'].mean().reset_index()
        course_avg = course_avg.sort_values('assessment_score', ascending=False)

        colors = ['#FF8C42', '#50C878', '#9B59B6', '#4A90E2', '#FFD93D']
        fig_course = go.Figure(data=[
            go.Pie(labels=course_avg['course_name'],
                   values=course_avg['assessment_score'],
                   marker=dict(colors=colors),
                   textinfo='label+percent',
                   textposition='auto',
                   textfont=dict(size=11),
                   hovertemplate='<b>%{label}</b><br>Avg Score: %{value:.1f}<extra></extra>')
        ])
        fig_course.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        st.plotly_chart(fig_course, use_container_width=True)

    st.markdown("---")

    # Assessment Progression
    st.header("Assessment Progression")
    st.subheader("Average Score Over Time")

    progression = df.groupby('assessment_no')['assessment_score'].mean().reset_index()

    fig_progression = go.Figure()
    fig_progression.add_trace(go.Scatter(
        x=progression['assessment_no'],
        y=progression['assessment_score'],
        mode='lines+markers+text',
        marker=dict(size=12, color='#4A90E2'),
        line=dict(width=3, color='#4A90E2'),
        text=progression['assessment_score'].round(1),
        textposition='top center',
        textfont=dict(size=12, color='#1f1f1f')
    ))
    fig_progression.add_hline(y=PASSING_SCORE, line_dash="dash", line_color="red",
                              annotation_text="Passing (60)", annotation_position="right")
    fig_progression.update_layout(
        xaxis_title="Assessment Number",
        yaxis_title="Average Score",
        height=400,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1),
        margin=dict(l=40, r=40, t=60, b=60),
        yaxis=dict(range=[0, 100])
    )
    st.plotly_chart(fig_progression, use_container_width=True)

    trend = "improving" if progression.iloc[-1]['assessment_score'] > progression.iloc[0][
        'assessment_score'] else "declining"
    st.info(
        f"✅ {'Positive' if trend == 'improving' else 'Negative'} trend: Students are showing {trend} performance over time")

    st.markdown("---")

    # Engagement vs Performance
    st.header("Engagement vs Performance")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Attendance Impact")
        attendance_bins = pd.cut(df['attendance_rate'], bins=[0, 60, 100], labels=['40-60%', '80-100%'])
        attendance_impact = df.groupby(attendance_bins)['assessment_score'].mean().reset_index()

        fig_attendance = go.Figure(data=[
            go.Bar(x=attendance_impact['attendance_rate'],
                   y=attendance_impact['assessment_score'],
                   marker_color=['#FF6B6B', '#6BCB77'],
                   text=attendance_impact['assessment_score'].round(1),
                   textposition='outside',
                   textfont=dict(size=14, color='#1f1f1f'))
        ])
        fig_attendance.add_hline(y=PASSING_SCORE, line_dash="dash", line_color="gray")
        fig_attendance.update_layout(
            height=350,
            showlegend=False,
            xaxis_title="Attendance Range",
            yaxis_title="Avg Score",
            margin=dict(l=40, r=40, t=50, b=60),
            yaxis=dict(range=[0, attendance_impact['assessment_score'].max() * 1.15])
        )
        st.plotly_chart(fig_attendance, use_container_width=True)

    with col2:
        st.subheader("Class Participation Impact")
        participation_bins = pd.cut(df['raised_hand_count'], bins=[0, 15, 30], labels=['Low (0-15)', 'High (30+)'])
        participation_impact = df.groupby(participation_bins)['assessment_score'].mean().reset_index()

        fig_participation = go.Figure(data=[
            go.Bar(x=participation_impact['raised_hand_count'],
                   y=participation_impact['assessment_score'],
                   marker_color=['#FF8C42', '#6BCB77'],
                   text=participation_impact['assessment_score'].round(1),
                   textposition='outside',
                   textfont=dict(size=14, color='#1f1f1f'))
        ])
        fig_participation.add_hline(y=PASSING_SCORE, line_dash="dash", line_color="gray")
        fig_participation.update_layout(
            height=350,
            showlegend=False,
            xaxis_title="Participation Level",
            yaxis_title="Avg Score",
            margin=dict(l=40, r=40, t=50, b=60),
            yaxis=dict(range=[0, participation_impact['assessment_score'].max() * 1.15])
        )
        st.plotly_chart(fig_participation, use_container_width=True)

    with col3:
        st.subheader("Online Engagement Impact")

        # Create engagement bins
        df_temp = df.copy()
        df_temp['engagement_level'] = pd.cut(df_temp['moodle_views'],
                                             bins=[0, 20, 40, 60, 80, 100],
                                             labels=['0-20', '20-40', '40-60', '60-80', '80-100'])
        df_temp['score_level'] = pd.cut(df_temp['assessment_score'],
                                        bins=[0, 40, 60, 80, 100],
                                        labels=['0-40', '40-60', '60-80', '80-100'])

        # Create heatmap data
        heatmap_data = df_temp.groupby(['engagement_level', 'score_level']).size().reset_index(name='count')
        heatmap_pivot = heatmap_data.pivot(index='score_level', columns='engagement_level', values='count').fillna(0)

        fig_engagement = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            colorscale='Blues',
            text=heatmap_pivot.values.astype(int),
            texttemplate='%{text}',
            textfont={"size": 12},
            hovertemplate='Moodle Views: %{x}<br>Score Range: %{y}<br>Students: %{z}<extra></extra>'
        ))

        fig_engagement.update_layout(
            height=350,
            xaxis_title="Moodle Views Range",
            yaxis_title="Score Range",
            margin=dict(l=40, r=40, t=50, b=60)
        )
        st.plotly_chart(fig_engagement, use_container_width=True)

    st.markdown("---")

    # Risk Overview with SPI
    st.header("Risk Overview")
    col1, col2 = st.columns(2)

    # Calculate at-risk students using SPI
    student_avg = df.groupby('student_id').agg({
        'assessment_score': 'mean',
        'attendance_rate': 'mean',
        'raised_hand_count': 'mean',
        'class_level': 'first',
        'student_name': 'first'
    }).reset_index()

    # Apply SPI calculation to each student
    spi_results = []
    for student_id in student_avg['student_id']:
        student_data = df[df['student_id'] == student_id]
        spi_score, status, status_color, details = calculate_student_performance_index(student_data, PASSING_SCORE)
        spi_results.append({
            'student_id': student_id,
            'spi_score': spi_score,
            'status': status,
            'status_color': status_color
        })

    spi_df = pd.DataFrame(spi_results)
    student_avg = student_avg.merge(spi_df, on='student_id')

    # Define at-risk as students with AT RISK or CRITICAL status
    student_avg['at_risk'] = student_avg['status'].isin(['AT RISK', 'CRITICAL'])

    at_risk_by_class = student_avg[student_avg['at_risk']].groupby('class_level').size().reset_index(name='count')
    total_students = student_avg['student_id'].nunique()
    at_risk_total = student_avg['at_risk'].sum()
    passing_total = total_students - at_risk_total

    with col1:
        st.subheader("At-Risk Students by Class Level")

        fig_risk = go.Figure(data=[
            go.Bar(x=at_risk_by_class['class_level'],
                   y=at_risk_by_class['count'],
                   marker_color='#FF6B6B',
                   text=at_risk_by_class['count'],
                   textposition='outside',
                   textfont=dict(size=14, color='#1f1f1f'))
        ])
        fig_risk.update_layout(
            height=350,
            showlegend=False,
            margin=dict(l=40, r=40, t=50, b=60),
            yaxis=dict(range=[0, at_risk_by_class['count'].max() * 1.15] if len(at_risk_by_class) > 0 else [0, 10])
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    with col2:
        st.subheader("Overall Student Status")

        # Count students by status
        status_counts = student_avg['status'].value_counts()
        status_colors_map = {
            'EXCELLENT': '#2E7D32',
            'SATISFACTORY': '#F57C00',
            'AT RISK': '#EF6C00',
            'CRITICAL': '#C62828'
        }

        status_order = ['EXCELLENT', 'SATISFACTORY', 'AT RISK', 'CRITICAL']
        status_labels = [s for s in status_order if s in status_counts.index]
        status_values = [status_counts[s] for s in status_labels]
        status_colors = [status_colors_map[s] for s in status_labels]

        fig_status = go.Figure(data=[
            go.Pie(labels=status_labels,
                   values=status_values,
                   marker=dict(colors=status_colors),
                   hole=0.5,
                   textinfo='label+value+percent',
                   textfont=dict(size=12))
        ])
        fig_status.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # At-Risk Students Analysis with SPI
    st.header("⚠️ At-Risk Students Analysis")

    class_levels = sorted(student_avg['class_level'].unique())
    tabs = st.tabs([f"C {cl.replace('C', '')}" for cl in class_levels])

    for idx, cl in enumerate(class_levels):
        with tabs[idx]:
            at_risk_students = student_avg[
                (student_avg['class_level'] == cl) &
                (student_avg['at_risk'] == True)
                ].sort_values('spi_score')

            st.markdown(f"### C {cl.replace('C', '')} ({len(at_risk_students)} at risk)")

            if len(at_risk_students) > 0:
                st.markdown("**Students classified as AT RISK or CRITICAL based on Student Performance Index (SPI):**")
                st.markdown(f"- SPI < 65 (considers academics, attendance, engagement, failures, and trends)")
                st.markdown("")

                for _, student in at_risk_students.iterrows():
                    status_emoji = "🔴" if student['status'] == 'CRITICAL' else "⚠️"
                    with st.expander(
                            f"{status_emoji} {student['student_name']} - SPI: {student['spi_score']:.1f} ({student['status']})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown("**Avg Score**")
                            st.markdown(f"{student['assessment_score']:.1f}")
                        with col2:
                            st.markdown("**Attendance**")
                            st.markdown(f"{student['attendance_rate']:.1f}%")
                        with col3:
                            st.markdown("**Engagement**")
                            st.markdown(f"{student['raised_hand_count']:.0f}")

                        # Get detailed SPI breakdown
                        student_data = df[df['student_id'] == student['student_id']]
                        _, _, _, spi_details = calculate_student_performance_index(student_data, PASSING_SCORE)

                        st.markdown("**Contributing Factors:**")
                        if student['assessment_score'] < PASSING_SCORE:
                            st.markdown(f"- Failing average (below {PASSING_SCORE})")
                        if student['attendance_rate'] < 70:
                            st.markdown("- Low attendance")
                        if student['raised_hand_count'] < 10:
                            st.markdown("- Minimal engagement")
                        if spi_details['failed_courses'] > 0:
                            st.markdown(f"- Failing {spi_details['failed_courses']} course(s)")
                        if spi_details['trend_penalty'] > 0:
                            st.markdown(
                                f"- Declining performance trend ({spi_details['performance_trend']:.1f} point drop)")
            else:
                st.success(f"No at-risk students in C {cl.replace('C', '')}")

    st.markdown("---")

    # Priority Actions
    st.error("### ⚠️ Priority Actions Required")
    st.markdown(f"• **{at_risk_total} students** are currently at risk (AT RISK or CRITICAL status)")

    # Count CRITICAL students
    critical_students = student_avg[student_avg['status'] == 'CRITICAL']
    if len(critical_students) > 0:
        st.markdown(f"• **{len(critical_students)} students in CRITICAL status** require immediate intervention")

    st.markdown("• Schedule parent-teacher conferences for students with multiple risk factors")
    st.markdown("• Consider tutoring programs for students with critically low grades")
    st.markdown("• Address attendance barriers through counseling or family support services")
    st.markdown("• Implement engagement strategies for students showing minimal participation")

    st.markdown("---")

    # Student Search Section
    st.header("Student Performance Lookup")

    # Container for the search to make it distinct
    st.markdown('<div class="search-container">', unsafe_allow_html=True)

    st.markdown("### Search by ID")

    # Prepare dropdown options
    unique_students = df[['student_id', 'student_name']].drop_duplicates().sort_values('student_id')
    student_options = unique_students['student_id'].astype(str).tolist()

    # Dropdown with Placeholder
    default_index = 0
    search_options = ["Choose a student..."] + student_options

    selected_option = st.selectbox(
        "Select a Student ID",
        search_options,
        index=0,
        label_visibility="collapsed"
    )

    # The Blue Info Box
    st.markdown("""
    <div class="blue-info-box">
        <span style="margin-right: 10px; font-size: 1.2rem;">ℹ️</span>
        <strong>Select a Student ID to view details.</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Logic to display results when a student is selected
    if selected_option != "Choose a student...":
        try:
            student_id = int(selected_option)
            student_data = df[df['student_id'] == student_id]

            if len(student_data) > 0:
                # Calculate student metrics using SPI
                avg_score = student_data['assessment_score'].mean()
                avg_attendance = student_data['attendance_rate'].mean()
                avg_engagement = student_data['raised_hand_count'].mean()
                student_name = student_data.iloc[0]['student_name']
                class_level = student_data.iloc[0]['class_level']
                gender = student_data.iloc[0]['student_gender']

                # Get SPI-based status
                spi_score, status, status_color, spi_details = calculate_student_performance_index(student_data, PASSING_SCORE)

                # Count passing courses
                courses_performance = student_data.groupby('course_name')['assessment_score'].mean()
                passing_courses = (courses_performance >= PASSING_SCORE).sum()
                total_courses = len(courses_performance)

                # Student Header Card with Avatar
                initials = "".join([n[0] for n in student_name.split()])
                avatar_url = f"https://ui-avatars.com/api/?name={student_name}&background=random&size=128"

                st.markdown(f"""
                <div style="background-color: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 20px;">
                            <img src="{avatar_url}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #f0f2f6;">
                            <div>
                                <h2 style="margin: 0; color: #1f1f1f;">{student_name}</h2>
                                <p style="margin: 5px 0 0 0; color: #666; font-size: 16px;">ID: {student_id} | Class: {class_level} | {gender}</p>
                                <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">SPI Score: {spi_score:.1f}/100</p>
                            </div>
                        </div>
                        <div style="background-color: {status_color}; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold;">
                            {status}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Metrics Row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 4px solid #4CAF50;">
                        <p style="margin: 0; color: #666; font-size: 14px;">Avg Score</p>
                        <h2 style="margin: 5px 0 0 0; color: #4CAF50;">{avg_score:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 4px solid #2196F3;">
                        <p style="margin: 0; color: #666; font-size: 14px;">Attendance</p>
                        <h2 style="margin: 5px 0 0 0; color: #2196F3;">{avg_attendance:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 4px solid #9C27B0;">
                        <p style="margin: 0; color: #666; font-size: 14px;">Engagement</p>
                        <h2 style="margin: 5px 0 0 0; color: #9C27B0;">{avg_engagement:.1f}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 4px solid #FF9800;">
                        <p style="margin: 0; color: #666; font-size: 14px;">Passing Courses</p>
                        <h2 style="margin: 5px 0 0 0; color: #FF9800;">{passing_courses}/{total_courses}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # SPI Breakdown Section
                st.subheader("📊 Student Performance Index (SPI) Breakdown")
                col_spi1, col_spi2 = st.columns(2)

                with col_spi1:
                    st.markdown(f"""
                    **Base Components:**
                    - Academic (60%): {spi_details['academic_component']:.1f} points
                    - Attendance (25%): {spi_details['attendance_component']:.1f} points
                    - Engagement (15%): {spi_details['engagement_component']:.1f} points
                    - **Base SPI**: {spi_details['base_spi']:.1f} points
                    """)

                with col_spi2:
                    st.markdown(f"""
                    **Penalties Applied:**
                    - Failed Courses: -{spi_details['failure_penalty']} points ({spi_details['failed_courses']} course(s))
                    - Performance Trend: -{spi_details['trend_penalty']} points ({spi_details['performance_trend']:.1f} point change)
                    - **Final SPI**: {spi_score:.1f}/100
                    """)

                st.markdown("<br>", unsafe_allow_html=True)

                # Two columns for Course Breakdown and Insights
                col_left, col_right = st.columns(2)

                with col_left:
                    st.subheader("📚 Course Breakdown")
                    course_performance = student_data.groupby('course_name')['assessment_score'].mean().reset_index()
                    course_performance = course_performance.sort_values('assessment_score', ascending=False)

                    fig_student = go.Figure(data=[
                        go.Bar(x=course_performance['course_name'],
                               y=course_performance['assessment_score'],
                               text=course_performance['assessment_score'].round(1),
                               textposition='outside',
                               textfont=dict(size=12, color='#1f1f1f'),
                               marker_color=['#4CAF50' if score >= PASSING_SCORE else '#EF5350'
                                             for score in course_performance['assessment_score']])
                    ])
                    fig_student.add_hline(y=PASSING_SCORE, line_dash="dash", line_color="red",
                                          annotation_text="Passing Line")
                    fig_student.update_layout(
                        height=350,
                        showlegend=False,
                        xaxis_title="Course",
                        yaxis_title="Average Score",
                        yaxis=dict(range=[0, max(course_performance['assessment_score'].max() * 1.2, 100)]),
                        margin=dict(l=40, r=40, t=40, b=60)
                    )
                    st.plotly_chart(fig_student, use_container_width=True)

                with col_right:
                    st.subheader("💡 Automated Insights")
                    insights = []

                    # SPI-based insights
                    if status == "EXCELLENT":
                        insights.append("✅ **Excellent Performance**: Student is performing exceptionally well across all metrics")
                    elif status == "SATISFACTORY":
                        insights.append("✅ **Satisfactory Performance**: Student is meeting expectations")
                    elif status == "AT RISK":
                        insights.append("⚠️ **At Risk**: Student needs support to improve performance")
                    else:  # CRITICAL
                        insights.append("🚨 **Critical Status**: Immediate intervention required")

                    # Academic insights
                    if avg_score >= 80:
                        insights.append("✅ **Strong Academics**: Consistently scoring above 80%")
                    elif avg_score >= 70:
                        insights.append("✅ **Good Academic Standing**: Maintaining solid grades")
                    elif avg_score >= PASSING_SCORE:
                        insights.append(f"⚠️ **Borderline Performance**: Scores just above passing threshold")
                    else:
                        insights.append(f"🚨 **Academic Emergency**: Failing average (below {PASSING_SCORE})")

                    # Attendance insights
                    if avg_attendance >= 90:
                        insights.append("✅ **Excellent Attendance**: Rarely misses class")
                    elif avg_attendance >= 80:
                        insights.append("✅ **Good Attendance**: Regular class participation")
                    elif avg_attendance >= 70:
                        insights.append("⚠️ **Attendance Concern**: Missing classes regularly")
                    else:
                        insights.append("🚨 **Poor Attendance**: Significant absences affecting performance")

                    # Engagement insights
                    if spi_details['normalized_engagement'] >= 80:
                        insights.append("✅ **Highly Engaged**: Exceptional class participation")
                    elif spi_details['normalized_engagement'] >= 50:
                        insights.append("✅ **Moderate Engagement**: Participates occasionally")
                    else:
                        insights.append("⚠️ **Low Engagement**: Rarely participates in class")

                    # Trend insights
                    if spi_details['trend_penalty'] > 0:
                        insights.append(f"📉 **Declining Trend**: Performance dropped by {abs(spi_details['performance_trend']):.1f} points")
                    elif spi_details['performance_trend'] > 10:
                        insights.append(f"📈 **Improving Trend**: Performance increased by {spi_details['performance_trend']:.1f} points!")

                    # Course failure insights
                    if spi_details['failed_courses'] > 0:
                        weak_courses = course_performance[course_performance['assessment_score'] < PASSING_SCORE]
                        course_list = ", ".join(weak_courses['course_name'].tolist())
                        insights.append(f"📚 **Failing {spi_details['failed_courses']} Course(s)**: {course_list}")

                    # Strong subjects
                    strong_courses = course_performance[course_performance['assessment_score'] >= 80]
                    if len(strong_courses) > 0:
                        course_list = ", ".join(strong_courses['course_name'].tolist())
                        insights.append(f"🌟 **Strong Subjects**: {course_list}")

                    for insight in insights:
                        st.markdown(insight)

                    # Recommendations based on SPI
                    st.markdown("---")
                    st.markdown("**📋 Recommendations:**")

                    if status == "CRITICAL":
                        st.markdown("• **URGENT**: Schedule immediate parent-teacher conference")
                        st.markdown("• Develop individualized academic support plan")
                        st.markdown("• Consider intensive tutoring services")
                        st.markdown("• Investigate barriers to attendance and engagement")
                    elif status == "AT RISK":
                        st.markdown("• Schedule parent-teacher conference")
                        st.markdown("• Provide targeted tutoring for failing courses")
                        st.markdown("• Monitor attendance and engagement closely")
                    elif status == "SATISFACTORY":
                        st.markdown("• Continue current support strategies")
                        st.markdown("• Encourage participation in challenging coursework")
                    else:  # EXCELLENT
                        st.markdown("• Consider advanced placement opportunities")
                        st.markdown("• Encourage peer tutoring/mentoring roles")

                # Detailed records
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("📄 View Detailed Assessment Records"):
                    display_data = student_data[['course_name', 'assessment_no', 'assessment_score',
                                                 'attendance_rate', 'raised_hand_count', 'moodle_views',
                                                 'resources_downloads']].copy()
                    display_data.columns = ['Course', 'Assessment #', 'Score', 'Attendance %',
                                            'Hand Raises', 'Moodle Views', 'Downloads']
                    st.dataframe(display_data, use_container_width=True)
            else:
                st.warning(f"No student found with ID: {student_id}")
        except ValueError:
            st.error("Please enter a valid student ID number")

except FileNotFoundError:
    st.error(
        "⚠️ Error: 'Students_Dataset.csv' not found. Please ensure the file is in the same directory as this script.")
except Exception as e:
    st.error(f"⚠️ An error occurred: {str(e)}")

    st.info("Please check that your CSV file is properly formatted and contains the required columns.")
