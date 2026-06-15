pub mod cemetery;
pub mod burial;
pub mod concession;
pub mod individual;
pub mod plot;

pub use cemetery::{CemeteryDTO, CreateCemeteryRequest, UpdateCemeteryRequest};
pub use burial::{BurialDTO, CreateBurialRequest};
pub use concession::{ConcessionDTO, CreateConcessionRequest, UpdateConcessionRequest};
pub use individual::{IndividualDTO, CreateIndividualRequest, UpdateIndividualRequest};
pub use plot::{PlotDTO, CreatePlotRequest, UpdatePlotRequest};
