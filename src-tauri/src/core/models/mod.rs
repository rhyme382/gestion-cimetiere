pub mod burial;
pub mod cemetery;
pub mod concession;
pub mod individual;
pub mod municipality;
pub mod plot;

pub use burial::Burial;
pub use cemetery::Cemetery;
pub use concession::{Concession, ConcessionStatus, ConcessionType};
pub use individual::Individual;
pub use municipality::Municipality;
pub use plot::Plot;
