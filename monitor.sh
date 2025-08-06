#!/bin/bash

# Discord 봇 컨테이너 모니터링 스크립트

CONTAINER_NAME="discord-bot-strange"
LOG_FILE="/var/log/discord-bot-monitor.log"

# 로그 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# 컨테이너 상태 확인
check_container() {
    if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
        log "컨테이너가 중지되었습니다: $CONTAINER_NAME"
        return 1
    fi
    return 0
}

# 컨테이너 재시작
restart_container() {
    log "컨테이너 재시작 시도: $CONTAINER_NAME"
    
    # Docker Compose로 재시작 시도
    if [ -f "docker-compose.yml" ]; then
        docker-compose restart discord-bot
        log "Docker Compose로 재시작 완료"
    else
        # 상위 폴더에서 실행
        cd ..
        if [ -f "docker-compose.yml" ]; then
            docker-compose restart discord-bot
            log "상위 폴더에서 Docker Compose로 재시작 완료"
        else
            # 직접 컨테이너 재시작
            docker restart $CONTAINER_NAME
            log "직접 컨테이너 재시작 완료"
        fi
    fi
}

# 메인 모니터링 루프
main() {
    log "Discord 봇 모니터링 시작"
    
    while true; do
        if ! check_container; then
            log "컨테이너 복구 시도"
            restart_container
            
            # 재시작 후 상태 확인
            sleep 10
            if check_container; then
                log "컨테이너 복구 성공"
            else
                log "컨테이너 복구 실패"
            fi
        fi
 
        # 30초마다 체크
        sleep 30
    done
}

# 스크립트 실행
main 