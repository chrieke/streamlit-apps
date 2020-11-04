from dateutil.parser import parse
import base64

import streamlit as st
from streamlit_folium import folium_static
import up42
import graphviz as graphviz
import geopandas as gpd

st.set_page_config(layout="centered",
                   initial_sidebar_state="expanded") #,page_icon="./logo.png")
st.title("UP42 APP")


####### PROJECT ######

## Auth & project
st.sidebar.markdown("Enter your [UP42 credentials](https://sdk.up42.com/authentication/):")
project_id = st.sidebar.text_input("Project ID", value='', max_chars=None, key=None, type='default')
project_apikey = st.sidebar.text_input("Project API KEY", value='', max_chars=None, key=None, type='default')

if not project_id or not project_apikey:
    st.sidebar.warning('Please input your credentials.')
    st.stop()
authentication_state = st.sidebar.text('Authenticating...')

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def authenticate():
    try:
        up42.authenticate(project_id=project_id, project_api_key=project_apikey)
        #up42.authenticate(cfg_file="config.json", env="dev")
        return None
    except ValueError as e:
        return e
autenticate_error = authenticate()
authentication_state.text(f"")
if autenticate_error is not None:
    st.sidebar.error(f'{autenticate_error}')
    st.stop()

project = up42.initialize_project()
authentication_state.text(f"")
st.sidebar.success('Authentication successfull!')
st.sidebar.text("\n")
st.sidebar.markdown(project)

#### WORKFLOW ####
st.header("Workflow")
workflow_name = "30-seconds-workflow"
input_tasks = ['sobloo-s2-l1c-aoiclipped', 'sharpening']

select_workflow = st.selectbox(
    'Select a workflow:',
     [workflow_name]) #"Some other workflow"
if select_workflow is None:
    # TODO: Needs None in list
    # TODO: Selectable need tasks below
    st.warning('Please select a workflow!')
    st.stop()

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def create_workflow(input_tasks):
    workflow = project.create_workflow(name=workflow_name,
                                       use_existing=True)
    workflow.add_workflow_tasks(input_tasks=input_tasks)
    return workflow

with st.spinner(f"Creating workflow '{workflow_name}"):
    workflow = create_workflow(input_tasks=input_tasks)
st.success(f"Successfully created/using workflow '{workflow_name}'")

col1_workflow, col2_workflow, col3_workflow = st.beta_columns([1,4,6])

dot = graphviz.Digraph()
for n in input_tasks:
    dot.node(n, n, shape='box')
dot.edge(*input_tasks)
col2_workflow.graphviz_chart(dot)

col3_workflow.markdown(workflow)

st.text("")
st.text("")
st.text("")


##### INPUT PARAMETERS ######


st.header("Select Workflow Parameters")
# Define the aoi and input parameters of the workflow.
col1_params, col2_params = st.beta_columns(2)

with col1_params:
    aoi_location = st.selectbox(
        'Which area of interest?',
         ["Berlin", "Washington"])
    aoi = up42.get_example_aoi(location=aoi_location, as_dataframe=True)
    # expander_aoi = st.beta_expander("Show aoi feature")
    # expander_aoi.json(aoi)

with col1_params:
    uploaded_file = st.file_uploader("Or upload a geojson file:",
                                     type=["geojson"])
    if uploaded_file is not None:
        aoi = gpd.read_file(uploaded_file, driver="GeoJSON")
        st.success("Using uploaded geojson as aoi!")

with col1_params:
    st.text("")
    start_date = st.date_input("Start date", parse("2019-01-01"))
    end_date = st.date_input("End date", parse("2020-01-01"))

with col1_params:
    limit = st.number_input(label='limit',
                             min_value=1,
                             max_value=10,
                             value=1,
                             step=1)

with col1_params:
    cloud_cover = st.slider('Select Cloud Cover 0-100:', 0, 100, 50)

with col1_params:
    sharpening_strength = st.radio(
     "Sharpening strength:",
     ('light', 'medium', 'strong'), index=1)

input_parameters = workflow.construct_parameters(geometry=aoi,
                                                 geometry_operation="bbox",
                                                 start_date="2019-01-01",
                                                 end_date="2020-01-01",
                                                 limit=limit)
input_parameters["sobloo-s2-l1c-aoiclipped:1"].update({"max_cloud_cover":cloud_cover})
input_parameters["sharpening:1"].update({"strength":sharpening_strength})
#expander = st.beta_expander("Show Input Parameters")
#expander.write(input_parameters)

with col2_params:
    st.json(input_parameters)

st.text("")
st.text("")

##### JOB ######
st.header("Execute Workflow")

button_testjob = st.button("RUN TEST JOB (OPTIONAL)")
if button_testjob:
    with st.spinner("Running Test Job ..."):
        # Run a test job to check data availability and configuration.
        test_job = workflow.test_job(input_parameters=input_parameters,
                                     track_status=True)
        #testjob_state.success(f"Successfully ran Test Job!")
        st.success("Test Job successfull!")
        expander_testjob = st.beta_expander("Click for Test Job result json")
        expander_testjob.json(test_job.get_results_json())

st.text("")
st.text("")


button_realjob = st.button("RUN Job")
if button_realjob:
    with st.spinner("Running Job ..."):
        # Run a test job to check data availability and configuration.
        job = workflow.run_job(input_parameters=input_parameters,
                               track_status=True)
        st.success("Job successful!")
        expander_job = st.beta_expander("Click for Job results json")
        expander_job.json(job.get_results_json())

        with st.spinner("Downloading results files"):
            job.download_results()

        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot(job.plot_results(figsize=(3,3)))

        m = job.map_results()
        folium_static(m)

st.text("")
st.text("")


###### CATALOG SEARCH ########

# st.header("Catalog Search")
# catalog = up42.initialize_catalog()
# search_params = catalog.construct_parameters(geometry=aoi,
#                                              start_date="2018-01-01",
#                                              end_date="2020-12-31",
#                                              sensors=["sentinel2"],
#                                              max_cloudcover=20,
#                                              sortby="cloudCoverage",
#                                              limit=3)
# search_results = catalog.search(search_params)
#
# st.dataframe(search_results.drop(columns='geometry'))
#
# def get_table_download_link(df):
#     """Generates a link allowing the data in a given panda dataframe to be downloaded
#     in:  dataframe
#     out: href string
#     """
#     csv = df.to_csv(index=False)
#     b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
#     href = f'<a href="data:file/csv;base64,{b64}" download="search_results.csv">Download as csv file</a>'
#     return href
#
# st.markdown(get_table_download_link(search_results), unsafe_allow_html=True)

# Visualize geometries
#st.write(search_results["providerProperties"].iloc[0].keys())
#a = [x["spatialCoverage"] for x in search_results["providerProperties"].to_list()]
#st.write(a)

# st.set_option('deprecation.showPyplotGlobalUse', False)
# st.pyplot(up42.plot_coverage(scenes=search_results))
#
#
# button_quicklooks = st.button("Get quicklooks")
# if button_quicklooks:
#     catalog.download_quicklooks(image_ids = search_results.id.to_list(),
#                                 sensor="sentinel2")
#     m = catalog.map_quicklooks(search_results, aoi=aoi)
#     folium_static(m)


####### Altair viz #########

# #st.dataframe(aoi)
# import altair as alt
# altair_plot = alt.Chart(aoi.drop(columns='geometry')) #.mark_geoshape().encode(
# #     color="properties.id:Q"
# # ).properties(
# #     projection={'type': 'identity', 'reflectY': True}
# # )
# st.write(altair_plot)