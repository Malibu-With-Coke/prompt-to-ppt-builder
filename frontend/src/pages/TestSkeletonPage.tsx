import React, { useState } from 'react';

const API_ENDPOINT = "https://px5m3uz2sa.execute-api.ap-northeast-2.amazonaws.com/prod";

const TestSkeletonPage: React.FC = () => {
    const [logs, setLogs] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    const runTest = async () => {
        setIsLoading(true);
        setLogs([]);
        try {
            const jobId = crypto.randomUUID();
            addLog(`1. 테스트 시작. 생성된 Job ID: ${jobId}`);

            // 1. Upload URL 요청
            addLog('2. S3 Presigned URL (upload-url) 발급 요청 중...');
            const uploadRes = await fetch(`${API_ENDPOINT}/jobs/upload-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jobId,
                    fileName: 'dummy_template.pptx',
                    fileType: 'template',
                    contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                })
            });
            
            if (!uploadRes.ok) throw new Error(`업로드 URL 발급 실패: ${uploadRes.status}`);
            const uploadData = await uploadRes.json();
            addLog(`✅ Presigned URL 발급 성공: ${uploadData.s3Key}`);

            // 2. 더미 파일 S3 업로드
            addLog('3. S3로 브라우저 직접 업로드 (Dummy PPT 파일)...');
            const dummyFile = new Blob(['dummy content for testing'], { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
            const s3Res = await fetch(uploadData.uploadUrl, {
                method: 'PUT',
                body: dummyFile,
                // Presigned URL 서명에 Content-Type이 포함되지 않으므로 헤더 제거
                // (헤더를 추가하면 서명 불일치로 S3가 403 반환)
            });

            if (!s3Res.ok) throw new Error(`S3 파일 업로드 실패: ${s3Res.status}`);
            addLog(`✅ S3 업로드 성공!`);

            // 3. Job 생성 호출
            addLog('4. 백엔드(Step Functions) 파이프라인 시작 (Create Job)...');
            const createJobRes = await fetch(`${API_ENDPOINT}/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jobId,
                    templateS3Key: uploadData.s3Key,
                    contentS3Key: "uploads/dummy/content.docx",
                    options: { tone: "테스트", target: "개발자", length: 5, aiEngine: "bedrock" }
                })
            });

            if (!createJobRes.ok) throw new Error(`Job 생성 실패: ${createJobRes.status}`);
            addLog(`✅ Job 및 Step Functions 실행 성공! 상태 폴링 시작...`);

            // 4. 상태 폴링
            let currentStatus = 'PENDING';
            while (currentStatus !== 'SUCCEEDED' && currentStatus !== 'FAILED') {
                addLog(`⏳ 현재 상태: ${currentStatus}... 2초 대기`);
                await new Promise(r => setTimeout(r, 2000));

                const statusRes = await fetch(`${API_ENDPOINT}/jobs/${jobId}`);
                if (!statusRes.ok) throw new Error(`상태 조회 실패: ${statusRes.status}`);
                const statusData = await statusRes.json();
                
                if (statusData.status !== currentStatus) {
                    addLog(`🔄 상태 변경 감지! [${currentStatus} -> ${statusData.status}]`);
                    currentStatus = statusData.status;
                }
            }

            if (currentStatus === 'SUCCEEDED') {
                addLog(`🎉 엔진 테스트 완벽 성공! Fargate 워커가 정상 종료되었습니다.`);
            } else {
                addLog(`❌ 엔진 테스트 실패. 상태: ${currentStatus}`);
            }

        } catch (err: any) {
            addLog(`🚨 에러 발생: ${err.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="p-10 max-w-4xl mx-auto bg-gray-900 min-h-screen text-gray-100 font-mono">
            <h1 className="text-3xl font-bold mb-6 text-blue-400">Walking Skeleton E2E Test</h1>
            <p className="mb-6 text-gray-400">이 페이지는 AWS 인프라(S3, Lambda, Step Functions, Fargate) 전체가 하나로 뚫려있는지 검증하는 디버깅 채널입니다.</p>
            
            <button 
                onClick={runTest} 
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded text-xl font-bold transition disabled:opacity-50"
            >
                {isLoading ? '테스트 실행 중...' : '🔥 파이프라인 전체 테스트 시작'}
            </button>

            <div className="mt-8 bg-black p-6 rounded-lg border border-gray-700 min-h-[300px]">
                <h2 className="text-xl mb-4 border-b border-gray-700 pb-2">Terminal Logs</h2>
                {logs.length === 0 ? (
                    <p className="text-gray-600 italic">대기 중...</p>
                ) : (
                    <div className="space-y-2">
                        {logs.map((log, idx) => (
                            <div key={idx} className={log.includes('✅') || log.includes('🎉') ? 'text-green-400' : log.includes('🚨') || log.includes('❌') ? 'text-red-400' : 'text-gray-300'}>
                                {log}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TestSkeletonPage;
