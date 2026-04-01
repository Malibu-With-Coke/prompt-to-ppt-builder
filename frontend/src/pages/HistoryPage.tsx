import { Link } from 'react-router-dom';

export default function HistoryPage() {
  const mockJobs = [
    { id: '#ST-98234', status: 'RUNNING', date: 'Oct 24, 2024' },
    { id: '#ST-98231', status: 'SUCCEEDED', date: 'Oct 23, 2024' },
    { id: '#ST-98229', status: 'FAILED', date: 'Oct 22, 2024' },
    { id: '#ST-98225', status: 'PENDING', date: 'Oct 21, 2024' },
  ];

  const renderBadge = (status: string) => {
    switch(status) {
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-100">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            RUNNING
          </span>
        );
      case 'SUCCEEDED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-green-50 text-green-700 border border-green-100">
            <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
            SUCCEEDED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-red-50 text-red-700 border border-red-100">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
            FAILED
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            PENDING
          </span>
        );
      default:
        return null;
    }
  };

  const getActionBtns = (status: string, id: string) => {
    if (status === 'RUNNING' || status === 'PENDING') {
      return (
        <Link to={`/jobs/${id.replace('#', '')}`} className="p-2 hover:bg-surface-container-high rounded-lg text-secondary transition-colors" title="View Progress">
          <span className="material-symbols-outlined">visibility</span>
        </Link>
      );
    }
    if (status === 'SUCCEEDED') {
      return (
        <>
          <button className="p-2 hover:bg-surface-container-high rounded-lg text-primary-container transition-colors" title="Download PPT">
            <span className="material-symbols-outlined">download</span>
          </button>
          <button className="p-2 hover:bg-surface-container-high rounded-lg text-secondary transition-colors">
            <span className="material-symbols-outlined">more_vert</span>
          </button>
        </>
      );
    }
    if (status === 'FAILED') {
      return (
        <>
          <button className="p-2 hover:bg-surface-container-high rounded-lg text-secondary transition-colors" title="View Error">
            <span className="material-symbols-outlined">error_outline</span>
          </button>
          <button className="p-2 hover:bg-surface-container-high rounded-lg text-secondary transition-colors" title="Retry">
            <span className="material-symbols-outlined">refresh</span>
          </button>
        </>
      );
    }
  };

  return (
    <div className="w-full h-full p-4 sm:p-8 md:p-12 max-w-7xl mx-auto flex-grow">
      
      <div className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div>
          <h3 className="text-4xl font-headline font-extrabold tracking-tight text-primary mb-2">Generation History</h3>
          <p className="text-secondary font-body">Track and manage your automated presentation workflows.</p>
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          <div className="relative flex-grow md:flex-grow-0">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm">search</span>
            <input 
              className="pl-10 pr-4 py-2.5 bg-surface-container-lowest rounded-lg border-none focus:ring-2 focus:ring-primary-fixed-dim shadow-sm text-sm w-full md:w-64 placeholder:text-outline" 
              placeholder="Search Jobs..." 
              type="text"
            />
          </div>
          <button className="px-4 py-2.5 bg-surface-container-lowest shadow-sm rounded-lg flex items-center justify-center gap-2 text-sm font-semibold hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-sm">filter_list</span>
            <span className="hidden sm:inline">Filter</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-surface-container-lowest rounded-xl shadow-[0_4px_20px_rgba(0,31,63,0.03)] border border-outline-variant/10 overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="bg-surface-container-low/50 border-b border-outline-variant/10">
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-secondary">Job ID</th>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-secondary">Status</th>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-secondary">Created At</th>
              <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-secondary text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {mockJobs.map(job => (
              <tr key={job.id} className="hover:bg-surface-container-low/30 transition-colors">
                <td className="px-6 py-5 font-mono text-sm font-semibold text-primary">{job.id}</td>
                <td className="px-6 py-5">
                  {renderBadge(job.status)}
                </td>
                <td className="px-6 py-5 text-sm text-secondary">{job.date}</td>
                <td className="px-6 py-5 text-right">
                  <div className="flex justify-end gap-2 text-secondary">
                    {getActionBtns(job.status, job.id)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8 flex items-center justify-between text-sm text-secondary">
        <div>Showing 4 of 48 generation jobs</div>
        <div className="flex gap-2">
          <button className="w-10 h-10 flex items-center justify-center rounded-lg bg-surface-container-highest text-primary font-bold transition-colors">1</button>
          <button className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-container-highest transition-colors">2</button>
          <button className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-container-highest transition-colors">3</button>
          <button className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-container-highest transition-colors">
            <span className="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>

    </div>
  );
}
